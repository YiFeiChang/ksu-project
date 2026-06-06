using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using InfluxDB.Client;
using InfluxDB.Client.Api.Domain;
using InfluxDB.Client.Writes;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace KSU.Project.Pi.WebService.Services
{
    public class TcpGatewayService : BackgroundService
    {
        private ILogger<TcpGatewayService> Logger => _logger;
        private readonly ILogger<TcpGatewayService> _logger;
        private IConfiguration Configuration => _configuration;
        private readonly IConfiguration _configuration;
        private ConcurrentDictionary<string, double> DataCache => _dataCache;
        private readonly ConcurrentDictionary<string, double> _dataCache = new ConcurrentDictionary<string, double>();
        private X509Certificate2? ServerCertificate => _serverCertificate;
        private readonly X509Certificate2? _serverCertificate;
        private InfluxDbService InfluxDbService => _influxDbService;
        private readonly InfluxDbService _influxDbService;
        private ConcurrentDictionary<string, StreamWriter> ActiveClients => _activeClients;
        private readonly ConcurrentDictionary<string, StreamWriter> _activeClients = new ConcurrentDictionary<string, StreamWriter>();
        private Encoding Encoding => _encoding;
        private readonly Encoding _encoding = new UTF8Encoding(false);
        private ConcurrentDictionary<string, Dictionary<string, int>> ClientGpioPins => _clientGpioPins;
        private readonly ConcurrentDictionary<string, Dictionary<string, int>> _clientGpioPins = new ConcurrentDictionary<string, Dictionary<string, int>>();

        public TcpGatewayService(IConfiguration configuration, ILogger<TcpGatewayService> logger, InfluxDbService influxDbService)
        {
            _configuration = configuration;
            _logger = logger;
            _influxDbService = influxDbService;
            string certPath = Configuration["TCPGATEWAY_SSL_CERT_PATH"] ?? "";
            string certPassword = Configuration["TCPGATEWAY_SSL_CERT_PASSWORD"] ?? "";
            if (string.IsNullOrWhiteSpace(certPath) == false && System.IO.File.Exists(certPath))
                _serverCertificate = new X509Certificate2(certPath, certPassword);
            else
                Logger.LogWarning("找不到憑證檔案: {CertPath}。請確定自簽憑證存在。", certPath);
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            Task
                uploaderTask = InfluxDbUploaderTaskAsync(stoppingToken),
                tcpServerTask = StartTcpServerAsync(stoppingToken);
            await Task.WhenAll(uploaderTask, tcpServerTask);
        }

        private async Task StartTcpServerAsync(CancellationToken stoppingToken)
        {
            string localAddress = Configuration.GetValue<string>("TCPGATEWAY_LOCAL_ADDRESS", "0.0.0.0")!;
            int port = Configuration.GetValue<int>("TCPGATEWAY_PORT", 5100);
            TcpListener listener = new TcpListener(IPAddress.Parse(localAddress), port);
            try
            {
                listener.Start();
                Logger.LogInformation("TCP Gateway 伺服器已啟動，監聽通訊埠：{Port} (啟用 TLS/SSL)", port);
                while (!stoppingToken.IsCancellationRequested)
                {
                    TcpClient client = await listener.AcceptTcpClientAsync(stoppingToken);
                    _ = HandleClientAsync(client, stoppingToken);
                }
            }
            catch (OperationCanceledException) { }
            catch (Exception ex)
            {
                Logger.LogError(ex, "TCP 伺服器發生異常。");
            }
            finally
            {
                listener.Stop();
            }
        }

        private async Task HandleClientAsync(TcpClient client, CancellationToken stoppingToken)
        {
            using (client)
            using (Stream stream = ServerCertificate == null ? client.GetStream() : new SslStream(client.GetStream(), false))
            {
                try
                {
                    if (stream is SslStream sslStream)
                        await sslStream.AuthenticateAsServerAsync(ServerCertificate!, clientCertificateRequired: false, checkCertificateRevocation: true);
                    using StreamReader reader = new StreamReader(stream, Encoding);
                    using StreamWriter writer = new StreamWriter(stream, Encoding) { AutoFlush = false };
                    string? clientName = null;
                    try
                    {
                        while (!stoppingToken.IsCancellationRequested)
                        {
                            string? line = await reader.ReadLineAsync(stoppingToken);
                            if (line == null)
                                break;
                            try
                            {
                                JsonElement payload = JsonSerializer.Deserialize<JsonElement>(line);
                                JsonElement actionProp;
                                if (payload.TryGetProperty("action", out actionProp) && actionProp.GetString() == "register")
                                {
                                    if (payload.TryGetProperty("name", out JsonElement nameProp) && !string.IsNullOrWhiteSpace(nameProp.GetString()))
                                    {
                                        if (clientName != null && clientName != nameProp.GetString())
                                        {
                                            ActiveClients.TryRemove(clientName, out _);
                                            ClientGpioPins.TryRemove(clientName, out _);
                                        }
                                        clientName = nameProp.GetString()!;
                                        ActiveClients[clientName] = writer;
                                        Dictionary<string, int> registeredPins = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
                                        if (payload.TryGetProperty("gpios", out JsonElement gpiosProp) && gpiosProp.ValueKind == JsonValueKind.Array)
                                        {
                                            foreach (JsonElement gpioElement in gpiosProp.EnumerateArray())
                                            {
                                                if (gpioElement.TryGetProperty("pin", out JsonElement pinProp) && pinProp.TryGetInt32(out int pin) &&
                                                    gpioElement.TryGetProperty("name", out JsonElement pinNameProp) && !string.IsNullOrWhiteSpace(pinNameProp.GetString()))
                                                {
                                                    registeredPins[pinNameProp.GetString()!] = pin;
                                                }
                                            }
                                        }
                                        ClientGpioPins[clientName] = registeredPins;
                                        Logger.LogInformation("客戶端 {ClientName} 註冊成功，包含 {Count} 個受控 GPIO Pins。", clientName, registeredPins.Count);
                                        object response = new { success = true, message = $"Registered as {clientName}" };
                                        await writer.WriteLineAsync(JsonSerializer.Serialize(response));
                                        await writer.FlushAsync();
                                    }
                                }
                                else if (payload.TryGetProperty("action", out actionProp) && actionProp.GetString() == "post")
                                {
                                    if (payload.TryGetProperty("id", out JsonElement idProp) && payload.TryGetProperty("value", out JsonElement valueProp))
                                    {
                                        string dataId = idProp.GetString()!;
                                        double dataValue = valueProp.GetDouble();
                                        DataCache[dataId] = dataValue;
                                        object response = new { success = true, message = "Data cached successfully" };
                                        await writer.WriteLineAsync(JsonSerializer.Serialize(response));
                                        await writer.FlushAsync();
                                    }
                                    else
                                    {
                                        object response = new { success = false, message = "Missing 'id' or 'value'" };
                                        await writer.WriteLineAsync(JsonSerializer.Serialize(response));
                                        await writer.FlushAsync();
                                    }
                                }
                                else if (payload.TryGetProperty("action", out actionProp) && actionProp.GetString() == "gpio_state")
                                {
                                    if (payload.TryGetProperty("pin", out JsonElement pinProp) && pinProp.TryGetInt32(out int pin) &&
                                        payload.TryGetProperty("state", out JsonElement stateProp))
                                    {
                                        bool state = stateProp.GetBoolean();
                                        Logger.LogInformation("接收到客戶端 {ClientName} 的 GPIO {Pin} 狀態: {State}", clientName, pin, state);
                                        
                                        string dataId = $"{clientName}_gpio_{pin}";
                                        DataCache[dataId] = state ? 1.0 : 0.0;
                                        
                                        object response = new { success = true, message = "GPIO state received" };
                                        await writer.WriteLineAsync(JsonSerializer.Serialize(response));
                                        await writer.FlushAsync();
                                    }
                                }
                            }
                            catch (JsonException)
                            {
                                object response = new { success = false, message = "Invalid JSON format" };
                                await writer.WriteLineAsync(JsonSerializer.Serialize(response));
                                await writer.FlushAsync();
                            }
                        }
                    }
                    finally
                    {
                        if (!string.IsNullOrEmpty(clientName))
                        {
                            ActiveClients.TryRemove(clientName, out _);
                            ClientGpioPins.TryRemove(clientName, out _);
                        }
                    }
                }
                catch (Exception ex)
                {
                    Logger.LogError(ex, "處理客戶端連線時發生錯誤: {RemoteEndPoint}", client.Client.RemoteEndPoint);
                }
            }
        }

        private async Task InfluxDbUploaderTaskAsync(CancellationToken stoppingToken)
        {
            string[] patterns = Configuration["TCPGATEWAY_TIME_MATCH_REGEXES"]?.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries) ?? Array.Empty<string>();
            List<Regex> regexList = new List<Regex>();
            Dictionary<string, bool> triggerStates = new Dictionary<string, bool>();
            foreach (string pattern in patterns)
            {
                string trimmedPattern = pattern.Trim();
                regexList.Add(new Regex(trimmedPattern, RegexOptions.Compiled));
                triggerStates[trimmedPattern] = false;
            }
            Logger.LogInformation("背景上傳任務已啟動... 當前套用的上傳時間規則為：{RegexList}", string.Join(", ", regexList.Select(r => r.ToString())));
            while (!stoppingToken.IsCancellationRequested)
            {
                DateTime now = DateTime.Now;
                string matchTimeString = now.ToString("HH:mm:ss");
                bool shouldUpload = false;
                foreach (Regex regex in regexList)
                {
                    string pattern = regex.ToString();
                    bool isMatch = regex.IsMatch(matchTimeString);
                    if (isMatch && !triggerStates[pattern])
                    {
                        shouldUpload = true;
                        triggerStates[pattern] = true;
                    }
                    else if (!isMatch && triggerStates[pattern])
                        triggerStates[pattern] = false;
                }
                if (shouldUpload && !DataCache.IsEmpty)
                {
                    KeyValuePair<string, double>[] dataToUpload = DataCache.ToArray();
                    int successCount = await InfluxDbService.WriteDeviceMeasurementsAsync(dataToUpload, stoppingToken);
                    Logger.LogInformation("已成功上傳 {SuccessCount} 筆當前數值至 InfluxDB。", successCount);
                }
                await Task.Delay(200, stoppingToken);
            }
        }

        public async Task SetGpioStateAsync(string clientName, string pinName, bool state)
        {
            if (!ClientGpioPins.TryGetValue(clientName, out Dictionary<string, int>? pins) || !pins.TryGetValue(pinName, out int pin))
            {
                Logger.LogWarning("嘗試控制未註冊或不存在的客戶端 GPIO Pin: {ClientName} - {PinName}", clientName, pinName);
                return;
            }
            object command = new { action = "set_gpio", pin = pin, state = state };
            await SendCommandAsync(clientName, command);
        }

        public async Task<bool?> GetGpioStateAsync(string clientName, string pinName)
        {
            if (!ClientGpioPins.TryGetValue(clientName, out Dictionary<string, int>? pins) || !pins.TryGetValue(pinName, out int pin))
            {
                Logger.LogWarning("嘗試讀取未註冊或不存在的客戶端 GPIO Pin: {ClientName} - {PinName}", clientName, pinName);
                return null;
            }
            string dataId = $"{clientName}_gpio_{pin}";
            DataCache.TryRemove(dataId, out _);
            object command = new { action = "get_gpio", pin = pin };
            await SendCommandAsync(clientName, command);
            for (int i = 0; i < 30; i++)
            {
                await Task.Delay(100);
                if (DataCache.TryGetValue(dataId, out double val))
                    return val > 0.5;
            }
            return null;
        }

        private async Task SendCommandAsync(string clientName, object command)
        {
            if (ActiveClients.TryGetValue(clientName, out StreamWriter? writer))
            {
                try
                {
                    string message = JsonSerializer.Serialize(command);
                    await writer.WriteLineAsync(message);
                    await writer.FlushAsync();
                }
                catch (Exception ex)
                {
                    Logger.LogWarning(ex, "向客戶端 {ClientName} 發送命令失敗", clientName);
                }
            }
            else
            {
                Logger.LogWarning("找不到目標客戶端: {ClientName}", clientName);
            }
        }
        
        public IEnumerable<string> GetActiveClients()
        {
            return ActiveClients.Keys.ToList();
        }
        
        public IEnumerable<string> GetClientGpioPins(string clientName)
        {
            if (ClientGpioPins.TryGetValue(clientName, out Dictionary<string, int>? pins))
            {
                return pins.Keys.ToList();
            }
            return Enumerable.Empty<string>();
        }
    }
}