<template>
    <v-app :theme="themeName">
        <v-app-bar app elevation="1">
            <v-toolbar-title class="font-weight-bold">
                <v-icon start>mdi-leaf</v-icon> 智慧環境監測儀表板
            </v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn icon @click="toggleTheme" title="切換主題">
                <v-icon>{{ isDark ? 'mdi-weather-night' : 'mdi-weather-sunny' }}</v-icon>
            </v-btn>
        </v-app-bar>

        <v-main class="bg-background">
            <v-container fluid class="fill-height d-flex flex-column pa-4">

                <!-- 上半部：當下環境數值卡片 -->
                <v-row class="flex-grow-0 w-100 mb-2">
                    <v-col cols="12" sm="4" md="2" v-for="(metric, key) in metricsConfig" :key="key">
                        <v-card class="fill-height d-flex flex-column align-center justify-center pa-3" elevation="2">
                            <v-icon :color="metric.color" size="32" class="mb-2">{{ metric.icon }}</v-icon>
                            <div class="text-subtitle-1 text-medium-emphasis">{{ metric.label }}</div>
                            <div class="text-h4 font-weight-black mt-1">
                                {{ latestMetrics[key] ?? '--' }}
                                <span class="text-h6 text-medium-emphasis">{{ metric.unit }}</span>
                            </div>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- 下半部：走勢圖與控制區 -->
                <v-row class="flex-grow-1 w-100">

                    <!-- 左側：72小時趨勢圖 (ECharts) -->
                    <v-col cols="12" md="8" class="d-flex flex-column">
                        <v-card elevation="2" class="flex-grow-1 d-flex flex-column pa-2" style="min-height: 480px;">
                            <v-card-title class="text-subtitle-1 font-weight-bold">
                                <v-icon start>mdi-chart-timeline-variant</v-icon> 過去 72 小時數值走勢
                            </v-card-title>
                            <div class="flex-grow-1 position-relative">
                                <!-- ECharts 渲染容器 -->
                                <div ref="chartRef" class="position-absolute w-100 h-100"></div>
                            </div>
                        </v-card>
                    </v-col>

                    <!-- 右側：即時影像與電燈控制 -->
                    <v-col cols="12" md="4" class="d-flex flex-column">

                        <!-- 即時影像區塊 -->
                        <v-card elevation="2" class="mb-4 d-flex flex-column flex-grow-1" style="min-height: 480px;">
                            <v-card-title class="text-subtitle-1 font-weight-bold">
                                <v-icon start>mdi-cctv</v-icon> 現場即時影像
                            </v-card-title>
                            <div class="flex-grow-1 position-relative bg-black rounded-b">
                                <img :src="webcamStreamUrl" alt="WebCam Stream"
                                    class="webcam-img position-absolute w-100 h-100" @error="onImageError" />
                            </div>
                        </v-card>

                        <!-- 設備控制區塊 -->
                        <v-card elevation="2" class="flex-grow-0 pa-2">
                            <v-card-title class="text-subtitle-1 font-weight-bold">
                                <v-icon start>mdi-lightbulb-multiple</v-icon> 設備控制
                            </v-card-title>
                            <v-card-text>
                                <v-row>
                                    <v-col cols="4" v-for="(light, index) in lights" :key="index" class="text-center">
                                        <v-switch v-model="light.state" :color="light.state ? 'warning' : 'grey'"
                                            :loading="light.loading" hide-details inset class="d-flex justify-center"
                                            @change="toggleLight(index)"></v-switch>
                                        <div class="mt-2 text-button">{{ light.label }}</div>
                                    </v-col>
                                </v-row>
                            </v-card-text>
                        </v-card>

                    </v-col>
                </v-row>

            </v-container>
        </v-main>
    </v-app>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, shallowRef, watch } from 'vue';
import { useTheme } from 'vuetify';
import axios, { type AxiosResponse } from 'axios';
import * as echarts from 'echarts';

// === 系統配置 ===
const API_BASE = '~/api';
const DEVICE_IDS: Record<string, string> = {
    temperature: 'NodeMCU-32S_temperature',
    humidity: 'NodeMCU-32S_humidity',
    pressure: 'NodeMCU-32S_pressure',
    illuminance: 'NodeMCU-32S_lux',
    soilMoisture: 'NodeMCU-32S_soil'
};
const GPIO_CLIENT_NAME = 'NodeMCU-32S';  // 替換為實際的 GPIO Client 設備名稱

// === 主題控制 ===
const theme = useTheme();
const isDark = ref(true);
const themeName = computed(() => isDark.value ? 'dark' : 'light');

const toggleTheme = () => {
    isDark.value = !isDark.value;
    theme.global.name.value = themeName.value;
};

// === 環境數值定義 ===
const metricsConfig = {
    temperature: { label: '溫度', unit: '°C', icon: 'mdi-thermometer', color: 'error' },
    humidity: { label: '濕度', unit: '%', icon: 'mdi-water-percent', color: 'info' },
    pressure: { label: '氣壓', unit: 'hPa', icon: 'mdi-gauge', color: 'deep-purple' },
    illuminance: { label: '照度', unit: 'lux', icon: 'mdi-brightness-5', color: 'warning' },
    soilMoisture: { label: '土壤濕度', unit: '%', icon: 'mdi-sprout', color: 'success' },
};

const latestMetrics = ref<Record<string, number | null>>({
    temperature: null,
    humidity: null,
    pressure: null,
    illuminance: null,
    soilMoisture: null
});

// === 電燈控制 ===
const lights = ref([
    { pin: 'Light 1', label: '植物燈', state: false, loading: false },
    { pin: 'Light 2', label: '保留 (1)', state: false, loading: false },
    { pin: 'Light 3', label: '保留 (2)', state: false, loading: false }
]);

// === 影像串流 ===
const webcamStreamUrl = ref(`${API_BASE}/WebCam/stream`);

const onImageError = (e: Event) => {
    const target = e.target as HTMLImageElement;
    // 避免無限重試，若影像加載失敗可顯示佔位圖
    target.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100%25" height="100%25" viewBox="0 0 400 300"%3E%3Crect fill="%23333" width="100%25" height="100%25"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-size="24"%3E影像無法載入%3C/text%3E%3C/svg%3E';
};

// === ECharts 趨勢圖 ===
const chartRef = ref<HTMLElement | null>(null);
// Use shallowRef for ECharts instance to prevent deep reactivity issues
const chartInstance = shallowRef<echarts.ECharts | null>(null);

const initChart = () => {
    if (chartRef.value) {
        const instance = echarts.init(chartRef.value, themeName.value);

        const chartColors: Record<string, string> = {
            temperature: '#F44336',    // error
            humidity: '#2196F3',       // info
            pressure: '#673AB7',       // deep-purple
            illuminance: '#FF9800',    // warning
            soilMoisture: '#4CAF50'    // success
        };

        const yAxis: any[] = [];
        const series: any[] = [];
        const legendData: string[] = [];

        const keys = Object.keys(metricsConfig) as Array<keyof typeof metricsConfig>;
        keys.forEach((key, index) => {
            const config = metricsConfig[key];
            legendData.push(config.label);

            const isLeft = index % 2 === 0;
            const offset = Math.floor(index / 2) * 60;

            yAxis.push({
                type: 'value',
                name: `${config.label} (${config.unit})`,
                position: isLeft ? 'left' : 'right',
                offset: offset,
                alignTicks: true,
                scale: true,
                axisLabel: {
                    formatter: (value: number) => value.toFixed(2) + config.unit
                },
                splitLine: { show: index === 0, lineStyle: { type: 'dashed', opacity: 0.3 } }
            });

            series.push({
                name: config.label,
                type: 'line',
                smooth: true,
                data: [],
                yAxisIndex: index,
                itemStyle: { color: chartColors[key] },
            });
        });

        instance.setOption({
            backgroundColor: 'transparent',
            tooltip: { trigger: 'axis' },
            legend: { data: legendData, top: 0 },
            grid: { left: '15%', right: '15%', bottom: '5%', top: '20%', containLabel: true },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: []
            },
            yAxis: yAxis,
            series: series
        });

        chartInstance.value = instance;
    }
};

const renderChart = (timestamps: string[], seriesData: Record<string, (number | null)[]>) => {
    if (!chartInstance.value) return;

    const keys = Object.keys(metricsConfig) as Array<keyof typeof metricsConfig>;

    chartInstance.value.setOption({
        xAxis: {
            data: timestamps
        },
        series: keys.map(key => ({
            data: seriesData[key]
        }))
    });
};

// 監聽主題變化，重新渲染 ECharts
watch(isDark, () => {
    if (chartInstance.value) {
        chartInstance.value.dispose();
        initChart();
        fetchTrendData(); // 使用新主題重繪
    }
});

// === API 呼叫 ===
const fetchLatestMetrics = async () => {
    // 並行發送所有設備的最新數值請求
    const requests = Object.entries(DEVICE_IDS).map(async ([key, deviceId]) => {
        try {
            const { data } = await axios.get(`${API_BASE}/Measurements/latest/${deviceId}`);
            // 確保回傳資料存在，且包含 value 欄位
            if (data && data.value != null) {
                latestMetrics.value[key] = Number(data.value.toFixed(2));
            }
        } catch (error) {
            console.error(`無法取得最新監測數據 (${key})`, error);
        }
    });
    await Promise.all(requests);
};

const fetchTrendData = async () => {
    try {
        const metricKeys = Object.keys(DEVICE_IDS) as Array<keyof typeof DEVICE_IDS>;
        const requests = metricKeys.map(key =>
            axios.get(`${API_BASE}/Measurements`, { params: { deviceId: DEVICE_IDS[key], start: '-72h', aggregateWindow: '1h' } })
        );

        const responses: AxiosResponse<any, any, {}>[] = await Promise.all(requests);

        const timestamps: string[] = [];
        const seriesData: Record<string, (number | null)[]> = {};
        metricKeys.forEach(key => {
            seriesData[key] = [];
        });

        // 使用第一個指標 (溫度) 的時間軸作為基準
        const baseData = responses[0]?.data;
        if (!baseData || baseData.length === 0) {
            renderChart([], {}); // 沒有數據時渲染空圖表
            return;
        }

        baseData.forEach((d: any) => {
            const tDate = new Date(d.timestamp || d.time);
            timestamps.push(tDate.toLocaleTimeString('zh-TW', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }));

            metricKeys.forEach((key, i) => {
                const matchedData = responses[i]?.data.find((item: any) => new Date(item.timestamp || item.time).getTime() === tDate.getTime());
                seriesData[key]?.push(matchedData ? Number(matchedData.value.toFixed(2)) : null);
            });
        });

        renderChart(timestamps, seriesData);
    } catch (error) {
        console.error('無法取得歷史趨勢數據', error);
    }
};

const fetchLightStates = async () => {
    for (const [index, light] of lights.value.entries()) {
        try {
            const { data } = await axios.get(`${API_BASE}/Gpio/${GPIO_CLIENT_NAME}/${light.pin}`);
            if (data.success && lights.value[index])
                lights.value[index].state = data.state;
        } catch (error) {
            console.error(`取得 ${light.label} 狀態失敗`, error);
        }
    }
};

const toggleLight = async (index: number) => {
    const light = lights.value[index];
    if (!light) return;
    light.loading = true;
    try {
        // 根據 C# 模型 public class GpioStateRequest { public bool State { get; set; } }
        await axios.post(`${API_BASE}/Gpio/${GPIO_CLIENT_NAME}/${light.pin}`, {
            State: light.state
        });
    } catch (error) {
        console.error(`控制 ${light.label} 失敗`, error);
        light.state = !light.state; // 若失敗則切回原狀態
    } finally {
        light.loading = false;
    }
};

// === 生命週期 ===
let metricsTimer: number;
let trendTimer: number;
let lightsTimer: number;

const handleResize = () => chartInstance.value?.resize();

onMounted(() => {
    theme.global.name.value = themeName.value;
    initChart();

    // 初始取得資料，並確保在 DOM 渲染後調整圖表大小
    Promise.all([
        fetchLatestMetrics(),
        fetchTrendData(),
        fetchLightStates()
    ]).then(() => {
        chartInstance.value?.resize();
    });

    window.addEventListener('resize', handleResize); // 監聽視窗大小變化以調整圖表

    // 設置輪詢，定時刷新資料
    const POLLING_INTERVAL = 10000; // 10 秒
    metricsTimer = window.setInterval(fetchLatestMetrics, POLLING_INTERVAL);
    trendTimer = window.setInterval(fetchTrendData, POLLING_INTERVAL);
    lightsTimer = window.setInterval(fetchLightStates, POLLING_INTERVAL);
});

onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    clearInterval(metricsTimer);
    clearInterval(trendTimer);
    clearInterval(lightsTimer);
    chartInstance.value?.dispose();
});
</script>

<style scoped>
.webcam-img {
    object-fit: cover;
    /* 確保影像撐滿並維持比例 */
}
</style>
