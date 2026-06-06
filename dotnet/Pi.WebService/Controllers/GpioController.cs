using Microsoft.AspNetCore.Mvc;
using KSU.Project.Pi.WebService.Services;
using System.Threading.Tasks;

namespace KSU.Project.Pi.WebService.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class GpioController : ControllerBase
    {
        private readonly TcpGatewayService _tcpGatewayService;

        public GpioController(TcpGatewayService tcpGatewayService)
        {
            _tcpGatewayService = tcpGatewayService;
        }

        [HttpPost("{clientName}/{pinName}")]
        public async Task<IActionResult> SetGpioState(string clientName, string pinName, [FromBody] GpioStateRequest request)
        {
            await _tcpGatewayService.SetGpioStateAsync(clientName, pinName, request.State);
            return Ok(new { success = true, message = $"Command sent to set {pinName} to {request.State} on {clientName}." });
        }

        [HttpGet("{clientName}/{pinName}")]
        public async Task<IActionResult> GetGpioState(string clientName, string pinName)
        {
            bool? state = await _tcpGatewayService.GetGpioStateAsync(clientName, pinName);
            if (state.HasValue)
            {
                return Ok(new { success = true, state = state.Value, message = $"Successfully retrieved {pinName} state from {clientName}." });
            }
            return StatusCode(504, new { success = false, message = $"Timeout or failed to get {pinName} state from {clientName}. Device might be offline." });
        }
    }

    /// <summary>
    /// 承載設定 GPIO 狀態用的模型
    /// </summary>
    public class GpioStateRequest
    {
        public bool State { get; set; }
    }
}