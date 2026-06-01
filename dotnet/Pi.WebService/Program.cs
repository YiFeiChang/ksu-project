using KSU.Project.Pi.WebService.Services;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using System.Runtime.InteropServices;
using System.Net.Http;

namespace KSU.Project.Pi.WebService
{
    public class Program
    {
        public static void Main(string[] args)
        {
            DotNetEnv.Env.Load();
            
            WebApplicationBuilder builder = WebApplication.CreateBuilder(args);
            builder.Services.AddControllers();
            builder.Services.AddEndpointsApiExplorer();
            builder.Services.AddSwaggerGen();
            builder.Services.AddHttpClient();
            builder.Services.AddSingleton<InfluxDbService>();
            builder.Services.AddSingleton<WebCamCaptureService>();
            builder.Services.AddHostedService(provider => provider.GetRequiredService<WebCamCaptureService>());
            builder.Services.AddSingleton<TcpGatewayService>();
            builder.Services.AddHostedService(provider => provider.GetRequiredService<TcpGatewayService>());


            WebApplication app = builder.Build();
            if (app.Environment.IsDevelopment() || true)
            {
                app.UseSwagger();
                app.UseSwaggerUI();
            }
            app.UseHttpsRedirection();
            app.UseAuthorization();
            app.UseDefaultFiles();
            app.UseStaticFiles();
            app.MapControllers();
            app.Run();
        }
    }
}