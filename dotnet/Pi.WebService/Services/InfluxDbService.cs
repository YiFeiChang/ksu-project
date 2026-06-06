using InfluxDB.Client;
using InfluxDB.Client.Api.Domain;
using InfluxDB.Client.Writes;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace KSU.Project.Pi.WebService.Services
{
    public class DeviceMeasurementData
    {
        public string DeviceId { get; set; } = string.Empty;
        public DateTime Timestamp { get; set; }
        public double Value { get; set; }
    }

    public class InfluxDbService
    {
        private ILogger<InfluxDbService> Logger => _logger;
        private readonly ILogger<InfluxDbService> _logger;

        private IConfiguration Configuration => _configuration;
        private readonly IConfiguration _configuration;
        private string DbUrl => _dbUrl;
        private readonly string _dbUrl;
        private string Bucket => _bucket;
        private readonly string _bucket;
        private string Org => _org;
        private readonly string _org;
        private string Token => _token;
        private readonly string _token;

        public InfluxDbService(ILogger<InfluxDbService> logger, IConfiguration configuration)
        {
            _logger = logger;
            _configuration = configuration;
            _dbUrl = Configuration["INFLUXDB_URL"]!;
            _bucket = Configuration["INFLUXDB_BUCKET"]!;
            _org = Configuration["INFLUXDB_ORG"]!;
            _token = Configuration["INFLUXDB_TOKEN"]!;
        }

        public async Task<int> WriteDeviceMeasurementsAsync(IEnumerable<KeyValuePair<string, double>> measurements, CancellationToken cancellationToken = default)
        {
            int successCount = 0;
            try
            {
                using InfluxDBClient client = new InfluxDBClient(DbUrl, Token);
                WriteApiAsync writeApi = client.GetWriteApiAsync();

                foreach (var kvp in measurements)
                {
                    try
                    {
                        var point = PointData.Measurement("sensor_measurement")
                            .Tag("device_id", kvp.Key)
                            .Field("value", kvp.Value);

                        await writeApi.WritePointAsync(point, Bucket, Org, cancellationToken);
                        successCount++;
                    }
                    catch (Exception ex)
                    {
                        Logger.LogError(ex, "寫入 device_id {DeviceId} 時發生錯誤。", kvp.Key);
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "寫入 InfluxDB 批次測量時發生例外錯誤。");
            }
            return successCount;
        }

        /// <summary>
        /// 讀取指定區間的時序資料，可支援選用聚合查詢 (Downsampling)
        /// </summary>
        /// <param name="deviceId">設備 ID (若為 null 則查詢全部設備)</param>
        /// <param name="start">起始時間 (預設 "-1h")</param>
        /// <param name="stop">結束時間 (預設 "now()")</param>
        /// <param name="aggregateWindow">聚合時間窗口 (例如 "1m", "1h")，若為 null 則取原始資料不聚合</param>
        /// <param name="aggregateFunction">聚合函數 (預設 "mean"，支援 "max", "min", "last" 等)</param>
        /// <param name="cancellationToken">CancellationToken</param>
        public async Task<List<DeviceMeasurementData>> ReadDeviceMeasurementsAsync(
            string? deviceId = null,
            string start = "-1h",
            string stop = "now()",
            string? aggregateWindow = null,
            string aggregateFunction = "mean",
            CancellationToken cancellationToken = default)
        {
            var results = new List<DeviceMeasurementData>();
            try
            {
                using InfluxDBClient client = new InfluxDBClient(DbUrl, Token);
                var queryApi = client.GetQueryApi();

                var queryBuilder = new StringBuilder($@"from(bucket: ""{Bucket}"")");
                queryBuilder.AppendLine($@" |> range(start: {start}, stop: {stop})");
                queryBuilder.AppendLine($@" |> filter(fn: (r) => r[""_measurement""] == ""sensor_measurement"")");
                queryBuilder.AppendLine($@" |> filter(fn: (r) => r[""_field""] == ""value"")");

                if (!string.IsNullOrEmpty(deviceId))
                {
                    queryBuilder.AppendLine($@" |> filter(fn: (r) => r[""device_id""] == ""{deviceId}"")");
                }

                // 若有指定時間窗口，套用 aggregateWindow 函數進行資料聚合
                if (!string.IsNullOrEmpty(aggregateWindow))
                {
                    queryBuilder.AppendLine($@" |> aggregateWindow(every: {aggregateWindow}, fn: {aggregateFunction}, createEmpty: false)");
                }

                var tables = await queryApi.QueryAsync(queryBuilder.ToString(), Org, cancellationToken);

                foreach (var record in tables.SelectMany(table => table.Records))
                {
                    if (record.GetValue() != null && record.GetTime() != null)
                    {
                        results.Add(new DeviceMeasurementData
                        {
                            Timestamp = record.GetTime().Value.ToDateTimeUtc(),
                            DeviceId = record.GetValueByKey("device_id")?.ToString() ?? string.Empty,
                            Value = Convert.ToDouble(record.GetValue())
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "讀取 InfluxDB 測量資料時發生例外錯誤。");
            }
            return results;
        }

        /// <summary>
        /// 取得指定設備當前最新的時序資料
        /// </summary>
        /// <param name="deviceId">設備 ID</param>
        /// <param name="searchRange">往前搜尋的範圍限制 (預設為 "-7d"，可依系統資料頻率縮短以增加效能)</param>
        /// <param name="cancellationToken">CancellationToken</param>
        public async Task<DeviceMeasurementData?> ReadLatestDeviceMeasurementAsync(
            string deviceId,
            string searchRange = "-7d",
            CancellationToken cancellationToken = default)
        {
            // 針對最新資料，呼叫前面宣告的方法並強制使用 last 函數，不用設定時間窗口
            var results = await ReadDeviceMeasurementsAsync(deviceId, searchRange, "now()", null, "last", cancellationToken);
            return results.LastOrDefault();
        }
    }
}