using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Concurrent;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using Webcam;
using static Webcam.WebCamService;

namespace KSU.Project.Pi.WebService.Services
{
    public class WebCamCaptureService : BackgroundService
    {
        private ILogger<WebCamCaptureService> Logger => _logger;
        private readonly ILogger<WebCamCaptureService> _logger;
        private IConfiguration Configuration => _configuration;
        private readonly IConfiguration _configuration;
        private int LastCaptureMinute { get; set; }
        private ConcurrentDictionary<Guid, Channel<byte[]>> Subscribers => _subscribers;
        private readonly ConcurrentDictionary<Guid, Channel<byte[]>> _subscribers = new ConcurrentDictionary<Guid, Channel<byte[]>>();

        public WebCamCaptureService(ILogger<WebCamCaptureService> logger, IConfiguration configuration)
        {
            _logger = logger;
            _configuration = configuration;
        }

        public Tuple<Guid, ChannelReader<byte[]>> Subscribe()
        {
            Guid id = Guid.NewGuid();
            Channel<byte[]> channel = Channel.CreateBounded<byte[]>(new BoundedChannelOptions(2)
            {
                FullMode = BoundedChannelFullMode.DropOldest
            });
            Subscribers.TryAdd(id, channel);
            return Tuple.Create(id, channel.Reader);
        }

        public void Unsubscribe(Guid id)
        {
            Subscribers.TryRemove(id, out _);
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            Logger.LogInformation("WebCamCaptureService is starting.");
            while (!stoppingToken.IsCancellationRequested)
            {
                try
                {
                    string grpcUrl = Configuration["WEBCAM_GRPC_URL"] ?? "http://localhost:50051";
                    using GrpcChannel channel = GrpcChannel.ForAddress(grpcUrl);
                    WebCamServiceClient client = new WebCamServiceClient(channel);
                    using AsyncServerStreamingCall<Frame> call = client.StreamVideo(new StreamRequest { Start = true }, cancellationToken: stoppingToken);
                    await foreach (Frame frame in call.ResponseStream.ReadAllAsync(stoppingToken))
                    {
                        if (frame.Data.Length > 0)
                        {
                            byte[] imageData = frame.Data.ToByteArray();
                            foreach (Channel<byte[]> subscriber in Subscribers.Values)
                            {
                                subscriber.Writer.TryWrite(imageData);
                            }
                            CheckAndCaptureFrame(imageData);
                        }
                    }
                }
                catch (RpcException ex) when (ex.StatusCode == Grpc.Core.StatusCode.Cancelled)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Logger.LogWarning(ex, "與 WebCam Server 斷線或發生錯誤，5 秒後嘗試重新連線...");
                    await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
                }
            }
            Logger.LogInformation("WebCamCaptureService is stopping.");
        }

        private void CheckAndCaptureFrame(byte[] imageData)
        {
            DateTime now = DateTime.Now;
            int currentMinute = now.Minute;
            if (currentMinute % 10 == 0 && currentMinute != LastCaptureMinute)
            {
                LastCaptureMinute = currentMinute;
                Logger.LogInformation("擷取影像，準備上傳...");
                _ = UploadViaScpCommandAsync(imageData, $"pi_{now:yyyyMMdd_HHmmss}.jpg");
            }
        }

        private async Task UploadViaScpCommandAsync(byte[] imageData, string fileName)
        {
            string tempFilePath = System.IO.Path.GetTempFileName();
            try
            {
                await System.IO.File.WriteAllBytesAsync(tempFilePath, imageData);
                string host = Configuration["WEBCAM_SCP_HOST"]!;
                string username = Configuration["WEBCAM_SCP_USERNAME"]!;
                string remoteDirectory = Configuration["WEBCAM_SCP_REMOTE_DIRECTORY"]!;
                string targetPath = $"{username}@{host}:{remoteDirectory}/{fileName}";
                System.Diagnostics.ProcessStartInfo processInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "scp",
                    Arguments = $"-q \"{tempFilePath}\" \"{targetPath}\"", // -q 為安靜模式，不輸出進度條
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                using System.Diagnostics.Process process = new System.Diagnostics.Process { StartInfo = processInfo };
                process.Start();
                await process.WaitForExitAsync();
                if (process.ExitCode == 0)
                    Logger.LogInformation("成功透過 SCP 指令上傳 {FileName} 至 {Host}", fileName, host);
                else
                {
                    string error = await process.StandardError.ReadToEndAsync();
                    Logger.LogError("透過 SCP 指令上傳 {FileName} 失敗，ExitCode: {ExitCode}，錯誤訊息: {Error}", fileName, process.ExitCode, error);
                }
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "執行 SCP 指令上傳 {FileName} 過程中發生例外錯誤。", fileName);
            }
            finally
            {
                if (System.IO.File.Exists(tempFilePath))
                {
                    try
                    {
                        System.IO.File.Delete(tempFilePath);
                    }
                    catch (Exception ex)
                    {
                        Logger.LogWarning(ex, "無法刪除暫存檔案: {TempFilePath}", tempFilePath);
                    }
                }
            }
        }
    }
}