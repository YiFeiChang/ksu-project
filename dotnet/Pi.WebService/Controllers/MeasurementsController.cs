using KSU.Project.Pi.WebService.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace KSU.Project.Pi.WebService.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class MeasurementsController : ControllerBase
    {
        private InfluxDbService InfluxDbService => _influxDbService;
        private readonly InfluxDbService _influxDbService;
        private ILogger<MeasurementsController> Logger => _logger;
        private readonly ILogger<MeasurementsController> _logger;

        public MeasurementsController(InfluxDbService influxDbService, ILogger<MeasurementsController> logger)
        {
            _influxDbService = influxDbService;
            _logger = logger;
        }

        /// <summary>
        /// 取得指定區間的設備測量資料 (支援聚合)
        /// </summary>
        [HttpGet]
        public async Task<ActionResult<List<DeviceMeasurementData>>> GetMeasurements(
            [FromQuery] string? deviceId = null,
            [FromQuery] string start = "-1h",
            [FromQuery] string stop = "now()",
            [FromQuery] string? aggregateWindow = null,
            [FromQuery] string aggregateFunction = "mean",
            CancellationToken cancellationToken = default)
        {
            Logger.LogInformation("開始查詢設備測量資料 - deviceId: {DeviceId}, start: {Start}, stop: {Stop}, aggregateWindow: {AggregateWindow}, aggregateFunction: {AggregateFunction}",
                deviceId ?? "ALL", start, stop, aggregateWindow ?? "NONE", aggregateFunction);
            List<DeviceMeasurementData> data = await InfluxDbService.ReadDeviceMeasurementsAsync(
                deviceId, start, stop, aggregateWindow, aggregateFunction, cancellationToken);
            Logger.LogInformation("成功取得 {Count} 筆測量資料。", data.Count);
            return Ok(data);
        }

        /// <summary>
        /// 取得指定設備的最新測量資料
        /// </summary>
        [HttpGet("latest/{deviceId}")]
        public async Task<ActionResult<DeviceMeasurementData>> GetLatestMeasurement([FromRoute] string deviceId, CancellationToken cancellationToken = default)
        {
            Logger.LogInformation("開始查詢設備 {DeviceId} 的最新測量資料", deviceId);
            DeviceMeasurementData? data = await InfluxDbService.ReadLatestDeviceMeasurementAsync(deviceId, "-7d", cancellationToken);
            if (data == null)
            {
                Logger.LogWarning("找不到設備 {DeviceId} 的最新測量資料。", deviceId);
                return NotFound(new { Message = $"找不到設備 {deviceId} 的最新資料" });
            }
            Logger.LogInformation("成功取得設備 {DeviceId} 的最新測量資料。", deviceId);
            return Ok(data);
        }
    }
}