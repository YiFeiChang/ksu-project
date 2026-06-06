using KSU.Project.Pi.WebService.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using System;
using System.Text;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace KSU.Project.Pi.WebService.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class WebCamController : ControllerBase
    {
        private WebCamCaptureService WebCamCaptureService => _webCamCaptureService;
        private readonly WebCamCaptureService _webCamCaptureService;

        public WebCamController(WebCamCaptureService webCamCaptureService)
        {
            _webCamCaptureService = webCamCaptureService;
        }

        [HttpGet("stream")]
        public async Task Stream()
        {
            Response.ContentType = "multipart/x-mixed-replace; boundary=frame";
            string boundary = "\r\n--frame\r\nContent-Type: image/jpeg\r\n\r\n";
            byte[] boundaryBytes = Encoding.ASCII.GetBytes(boundary);
            Tuple<Guid, ChannelReader<byte[]>> tuple = WebCamCaptureService.Subscribe();
            Guid subId = tuple.Item1;
            ChannelReader<byte[]> reader = tuple.Item2;
            try
            {
                await foreach (byte[]? frameData in reader.ReadAllAsync(HttpContext.RequestAborted))
                {
                    await Response.Body.WriteAsync(boundaryBytes, HttpContext.RequestAborted);
                    await Response.Body.WriteAsync(frameData, HttpContext.RequestAborted);
                    await Response.Body.FlushAsync();
                }
            }
            catch (OperationCanceledException) { }
            finally
            {
                WebCamCaptureService.Unsubscribe(subId);
            }
        }
    }
}