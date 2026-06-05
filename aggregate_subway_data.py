import csv
from datetime import datetime

CSV_FILE_PATH = "서울교통공사_역별 일별 시간대별 승하차인원 정보_20241231.csv"
HTML_FILE_PATH = "index.html"

# 1. CSV 파일 데이터 집계
print("1. CSV 파일에서 전체 고유 역의 평일/주말 평균 데이터 집계 시작...")
data = {}
total_rows = 0

with open(CSV_FILE_PATH, mode='r', encoding='cp949') as f:
    reader = csv.reader(f)
    header = next(reader) # 헤더 스킵
    
    for row in reader:
        total_rows += 1
        if len(row) < 26:
            continue
            
        station_name = row[4].strip()
        if not station_name:
            continue
            
        if row[5] != '승차':
            continue
            
        date_str = row[1]
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_type = '주말' if dt.weekday() >= 5 else '평일'
        except ValueError:
            continue
            
        if station_name not in data:
            data[station_name] = {
                '평일': {'sums': [0.0] * 20, 'dates': set()},
                '주말': {'sums': [0.0] * 20, 'dates': set()}
            }
            
        data[station_name][day_type]['dates'].add(date_str)
        for i in range(20):
            try:
                val = float(row[6 + i])
                data[station_name][day_type]['sums'][i] += val
            except ValueError:
                pass

print(f"   - CSV 분석 완료 (총 {total_rows}개 행, 고유 역: {len(data)}개)")

# 일평균 계산
final_database = {}
for station, day_data in sorted(data.items()):
    final_database[station] = {}
    for day_type in ['평일', '주말']:
        dates_count = len(day_data[day_type]['dates'])
        if dates_count > 0:
            final_database[station][day_type] = [round(s / dates_count) for s in day_data[day_type]['sums']]
        else:
            final_database[station][day_type] = [0] * 20

# 2. index.html의 자바스크립트 영역 시작점 찾기
print("2. index.html 파일 로드 및 HTML 구조 뼈대 추출...")
with open(HTML_FILE_PATH, mode='r', encoding='utf-8') as f:
    html_content = f.read()

script_start_marker = "const timeLabels = ['~06시'"
script_start_idx = html_content.find(script_start_marker)

if script_start_idx == -1:
    script_start_idx = html_content.find("<script>")
    if script_start_idx != -1:
        script_start_idx = html_content.find("\n", script_start_idx) + 1
    else:
        raise Exception("index.html에서 script 시작점을 찾지 못했습니다.")
else:
    script_start_idx = html_content.rfind("<script>", 0, script_start_idx)
    script_start_idx += 8

html_base = html_content[:script_start_idx]

# 3. 새로운 완벽한 자바스크립트 코드 구성 (f-string이 아닌 일반 string 포맷팅으로 이스케이프 에러 방지)
print("3. 동적 피크 알고리즘 및 템플릿 연동 JS 코드 조립...")

# rawDatabase JS 문자열 생성
raw_db_js = "        const rawDatabase = {\n"
for station, day_data in final_database.items():
    raw_db_js += f"            '{station}': {{\n"
    raw_db_js += f"                '평일': {day_data['평일']},\n"
    raw_db_js += f"                '주말': {day_data['주말']}\n"
    raw_db_js += f"            }},\n"
raw_db_js = raw_db_js.rstrip(",\n") + "\n        };\n"

# 자바스크립트 코드 템플릿 (치환 대상: __RAW_DATABASE_PLACEHOLDER__)
js_template = """
        const timeLabels = ['~06시', '06-07', '07-08', '08-09', '09-10', '10-11', '11-12', '12-13', '13-14', '14-15', '15-16', '16-17', '17-18', '18-19', '19-20', '20-21', '21-22', '22-23', '23-24', '24시~'];

__RAW_DATABASE_PLACEHOLDER__

        const contentMap = {
            'RESIDENTIAL': {
                title: "🏠 주거 중심형 (Bed Town) 역세권 상권 판정",
                description: "아침 시간대에 타 지역 직장 및 학교로의 승차 인원 유출이 가장 뚜렷하게 관측되는 주거 배후 상권입니다. 오후 및 저녁 귀가길 하차 패턴과 맞물려 있어, 인근 지역 중심의 구인/구직 타겟팅이 지극히 합리적입니다.",
                theme: "blue",
                colorClass: "bg-brand-blue-50 text-brand-blue-900 border-brand-blue-200",
                actions: []
            },
            'OFFICE': {
                title: "🏢 오피스 중심형 (Workplace) 역세권 상권 판정",
                description: "오전 8-9시 하차 트래픽이 지배적이며, 17-19시 사이 직장인 퇴근길 승차(유출)가 폭발적으로 집계되는 정형 오피스 밸리입니다. 주말 트래픽 급감에 따라 주중 최적화 전략이 요구됩니다.",
                theme: "orange",
                colorClass: "bg-brand-orange-50 text-brand-orange-950 border-brand-orange-200",
                actions: []
            },
            'CAMPUS_MIXED': {
                title: "🎨 지속 활성형 (Campus/Mixed) 복합 상권 판정",
                description: "요일과 주중/주말에 관계없이 청년층과 외부인 유입 트래픽이 늦은 심야(22시~막차시점)까지 매우 완만하고 높게 장시간 집계되는 종합 레저·소비 핵심 상권입니다.",
                theme: "emerald",
                colorClass: "bg-brand-emerald-50 text-brand-emerald-950 border-brand-emerald-200",
                actions: []
            }
        };

        let currentDay = '평일';
        let currentStation = '신림';
        let chartInstance = null;
        let selectedTimelineIndex = null;

        const backgroundZonesPlugin = {
            id: 'backgroundZones',
            beforeDatasetsDraw(chart, args, pluginOptions) {
                const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
                if (!pluginOptions || !pluginOptions.zones) return;

                pluginOptions.zones.forEach((zone, idx) => {
                    const startX = x.getPixelForValue(zone.start);
                    const endX = x.getPixelForValue(zone.end);
                    if (startX !== undefined && endX !== undefined) {
                        ctx.save();
                        if (selectedTimelineIndex !== null) {
                            if (selectedTimelineIndex === idx) {
                                ctx.fillStyle = zone.color.replace('0.12', '0.25');
                            } else {
                                ctx.fillStyle = zone.color.replace('0.12', '0.04');
                            }
                        } else {
                            ctx.fillStyle = zone.color;
                        }
                        ctx.fillRect(startX, top, endX - startX, bottom - top);
                        ctx.restore();
                    }
                });
            }
        };
        Chart.register(backgroundZonesPlugin);

        function refreshIcons() {
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }

        // 겹치지 않는 2시간 연속 Peak Top 3를 구하는 함수
        function getTop3Peaks(data) {
            const intervals = [];
            for (let i = 0; i < 19; i++) {
                intervals.push({
                    startIdx: i,
                    endIdx: i + 1,
                    val: data[i] + data[i + 1]
                });
            }
            
            intervals.sort((a, b) => b.val - a.val);
            
            const chosen = [];
            for (let i = 0; i < intervals.length; i++) {
                if (chosen.length === 3) break;
                const item = intervals[i];
                
                const isOverlapping = chosen.some(c => Math.abs(c.startIdx - item.startIdx) <= 1);
                if (!isOverlapping) {
                    chosen.push(item);
                }
            }
            
            while (chosen.length < 3) {
                const remaining = intervals.find(item => !chosen.some(c => c.startIdx === item.startIdx));
                if (remaining) chosen.push(remaining);
                else break;
            }
            
            function formatTime(idx) {
                if (idx === 0) return "05:00";
                if (idx === 19) return "24:00";
                const label = timeLabels[idx];
                return label.split('-')[0] + ":00";
            }
            
            function formatTimeEnd(idx) {
                if (idx === 0) return "06:00";
                if (idx === 19) return "01:00 (익일)";
                const label = timeLabels[idx];
                return label.split('-')[1] + ":00";
            }

            return chosen.map(item => {
                const range = `${formatTime(item.startIdx)} - ${formatTimeEnd(item.endIdx)}`;
                return {
                    startIdx: item.startIdx,
                    endIdx: item.endIdx,
                    timeRange: range,
                    value: item.val
                };
            });
        }

        // 피크 시간대에 맞는 최적의 비즈니스 제안서 텍스트 조립기
        function getActionProposal(peak, rank, station) {
            const start = peak.startIdx;
            
            let type = "MIDDAY";
            if (start >= 2 && start <= 4) type = "MORNING";
            else if (start >= 12 && start <= 15) type = "EVENING";
            else if (start >= 5 && start <= 8) type = "LUNCH";
            else if (start >= 16) type = "NIGHT";

            const contentConfig = {
                "MORNING": {
                    title: "구직자 대상 아침 출근길 라이브 푸시 마케팅",
                    desc: `${station}역 상권의 아침 출근 인구 **${peak.value.toLocaleString()}명**(${peak.timeRange} 일평균 승차)이 타 거점으로 대거 이탈 및 출근하는 시점입니다. 이 시간대 지하철 내부 모바일 집중도가 최고치에 달하므로, '퇴근길 동네 꿀알바 선점' 마케팅 푸시를 게재하여 앱 인게이지먼트를 확보합니다.`,
                    tip: `이동 중 스마트폰 체류율이 74% 이상으로 관측되는 황금 시간대입니다. ${station}역 기준 '도보 10분', '퇴근길 연계 알바' 메시지가 매우 유효합니다.`
                },
                "EVENING": {
                    title: "B2B 점주 대상 퇴근길 선점 유료 공고 부스팅 권유",
                    desc: `직장인들이 퇴근을 준비하며 대거 이탈하는 골든타임(${peak.timeRange} 일평균 **${peak.value.toLocaleString()}명** 승차 폭발)입니다. 스마트폰을 켜기 직전에 유료 광고 부스팅을 실행해야 유출되는 인구의 모바일 화면 선점이 극대화됩니다.`,
                    tip: `직장인들이 퇴근 전후 슬그머니 부업이나 단기 알바를 탐색하는 심리를 타겟팅하는 마케팅 부스팅 효과가 탁월합니다.`
                },
                "LUNCH": {
                    title: "직장인 런치 스파이크 대응 초단기 알바 셋팅",
                    desc: `점심시간 대기 포기로 인한 점주 손실을 막기 위해 런치 피크(${peak.timeRange} 일평균 승차 **${peak.value.toLocaleString()}명** 밀집 대응)에 집중 투입될 '3시간 스프린터' 상품을 제안합니다.`,
                    tip: `이 상권 점주들의 최고 고충인 점심 회전율 저하를 방어하며, 단기 근로를 희망하는 인근 대학생/긱워커를 유치하는 전략입니다.`
                },
                "NIGHT": {
                    title: "심야 교통망 연계 안심 귀가 마감조 큐레이션",
                    desc: `늦은 심야까지 활발한 소비 행태가 유지되며 마감 인원 유출(${peak.timeRange} 일평균 **${peak.value.toLocaleString()}명** 승차)이 집중되는 시점입니다. 주점, 요식 브랜드의 야간 마감조 수급을 위해 대중교통 막차 데이터를 매칭한 안전 보장형 템플릿 공고를 게재합니다.`,
                    tip: `'막차 연계', '교통비 지급' 등의 키워드가 들어간 마감조 전용 공고가 최적의 지원 수렴 패턴을 보여줍니다.`
                },
                "MIDDAY": {
                    title: "주중 유휴 인력 풀(대학생 공강/주부) 타겟 광고 연계",
                    desc: `출근인구가 빠져나간 ${station}역 배후 잔류 인구(${peak.timeRange} 일평균 **${peak.value.toLocaleString()}명** 승차) 중 주부나 공강인 대학생을 타겟으로 한 주중 미들타임 공고를 B2B 파트너에 연계 제안합니다.`,
                    tip: `동네 빵집, 브런치 카페, 베이커리 등 동네 유휴 인력 수급을 원하는 사장님들에게 공고 효율이 극대화되는 타임입니다.`
                }
            };
            
            return contentConfig[type];
        }

        function updateDashboard() {
            const currentData = rawDatabase[currentStation][currentDay];

            const morningSum = currentData[2] + currentData[3];
            const eveningSum = currentData[12] + currentData[13];
            const lateNightSum = currentData[16] + currentData[17];
            const pbi = eveningSum / morningSum;
            const lns = (lateNightSum / eveningSum) * 100;

            let zoneType = "CAMPUS_MIXED";
            if (pbi < 1.0) {
                zoneType = "RESIDENTIAL";
            } else if (lns < 35) {
                zoneType = "OFFICE";
            }

            const config = contentMap[zoneType];
            const peaks = getTop3Peaks(currentData);
            
            const computedActions = peaks.map((peak, idx) => {
                const proposal = getActionProposal(peak, idx, currentStation);
                return {
                    time: `${["오전", "점심", "오후", "저녁", "야간"][idx] || "시간대"} ${peak.timeRange}`,
                    title: proposal.title,
                    desc: proposal.desc,
                    tip: proposal.tip
                };
            });

            const computedZones = [
                { start: timeLabels[peaks[0].startIdx], end: timeLabels[peaks[0].endIdx], color: 'rgba(59, 130, 246, 0.12)' },
                { start: timeLabels[peaks[1].startIdx], end: timeLabels[peaks[1].endIdx], color: 'rgba(249, 115, 22, 0.12)' },
                { start: timeLabels[peaks[2].startIdx], end: timeLabels[peaks[2].endIdx], color: 'rgba(234, 179, 8, 0.12)' }
            ];

            const badge = document.getElementById('zone-badge');
            badge.innerText = config.title;
            badge.className = `inline-block text-xs font-extrabold px-3 py-1.5 rounded-full border transition-all duration-300 ${config.colorClass}`;

            config.actions = computedActions;

            if (chartInstance) {
                chartInstance.destroy();
            }

            let colorTheme = "#2563eb";
            if (zoneType === "OFFICE") colorTheme = "#ea580c";
            if (zoneType === "CAMPUS_MIXED") colorTheme = "#059669";

            const ctx = document.getElementById('subwayChart').getContext('2d');
            const chartBgGradient = ctx.createLinearGradient(0, 0, 0, 320);
            chartBgGradient.addColorStop(0, colorTheme + '25');
            chartBgGradient.addColorStop(1, colorTheme + '00');

            chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: timeLabels,
                    datasets: [{
                        label: `평균 승차 유동인구`,
                        data: currentData,
                        borderColor: colorTheme,
                        backgroundColor: chartBgGradient,
                        borderWidth: 3,
                        pointBackgroundColor: '#ffffff',
                        pointBorderColor: colorTheme,
                        pointBorderWidth: 2,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointHoverBackgroundColor: colorTheme,
                        pointHoverBorderColor: '#ffffff',
                        fill: true,
                        tension: 0.35
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleFont: { family: 'Plus Jakarta Sans', size: 11, weight: 'bold' },
                            bodyFont: { family: 'Plus Jakarta Sans', size: 11 },
                            padding: 8,
                            cornerRadius: 6,
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            displayColors: false,
                            callbacks: {
                                label: function (context) {
                                    return `승차인원: ${context.parsed.y.toLocaleString()} 명`;
                                }
                            }
                        },
                        backgroundZones: { zones: computedZones }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: '#e2e8f0',
                                borderDash: [5, 5],
                                drawTicks: false
                            },
                            ticks: {
                                font: { size: 9, family: 'Plus Jakarta Sans', weight: '500' },
                                color: '#64748b',
                                callback: function (value) {
                                    return value.toLocaleString();
                                }
                            },
                            border: { display: false }
                        },
                        x: {
                            grid: { display: false },
                            ticks: {
                                font: { size: 9, family: 'Plus Jakarta Sans', weight: '600' },
                                color: '#64748b',
                                maxRotation: 45,
                                minRotation: 45
                            }
                        }
                    }
                }
            });

            selectedTimelineIndex = null;
            resetSimulationView();
            refreshIcons();
        }

        function toggleDay(day) {
            currentDay = day;
            const btnWd = document.getElementById('btn-weekday');
            const btnWe = document.getElementById('btn-weekend');
            const tabBg = document.getElementById('tab-bg');

            if (day === '평일') {
                tabBg.style.left = '4px';
                btnWd.className = "relative z-10 w-1/2 text-center text-xs font-bold transition-all text-slate-900";
                btnWe.className = "relative z-10 w-1/2 text-center text-xs font-semibold transition-all text-slate-400 hover:text-slate-600";
            } else {
                tabBg.style.left = '82px';
                btnWe.className = "relative z-10 w-1/2 text-center text-xs font-bold transition-all text-slate-900";
                btnWd.className = "relative z-10 w-1/2 text-center text-xs font-semibold transition-all text-slate-400 hover:text-slate-600";
            }
            
            updateDashboard();
        }

        function changeStation() {
            currentStation = document.getElementById('station-select').value;
            updateDashboard();
        }

        function resetSimulationView() {
            document.getElementById('sim-placeholder').classList.remove('hidden');
            document.getElementById('sim-loading').classList.add('hidden');
            document.getElementById('sim-results').classList.add('hidden');
        }

        function calculateSimulationScore() {
            const job = document.getElementById('sim-job').value;
            const time = document.getElementById('sim-time').value;
            const currentData = rawDatabase[currentStation][currentDay];
            const morningSum = currentData[2] + currentData[3];
            const eveningSum = currentData[12] + currentData[13];
            const lateNightSum = currentData[16] + currentData[17];
            
            const pbi = eveningSum / morningSum;
            const lns = (lateNightSum / eveningSum) * 100;
            
            // 1. 선택된 시간대의 실제 평균 유동인구 및 해당 역의 최대 유동인구 추출
            let selectedTraffic = 0;
            if (time === "morning") selectedTraffic = (currentData[2] + currentData[3]) / 2;
            else if (time === "noon") selectedTraffic = (currentData[6] + currentData[7]) / 2;
            else if (time === "afternoon") selectedTraffic = (currentData[9] + currentData[10] + currentData[11]) / 3;
            else if (time === "evening") selectedTraffic = (currentData[13] + currentData[14]) / 2;
            else if (time === "night") selectedTraffic = (currentData[16] + currentData[17] + currentData[18]) / 3;

            const maxTraffic = Math.max(...currentData);
            const trafficFactor = maxTraffic > 0 ? (selectedTraffic / maxTraffic) : 0; // 0.0 ~ 1.0

            // 2. 상권 유형(zoneType) 판별
            let zoneType = "CAMPUS_MIXED";
            if (pbi < 1.0) zoneType = "RESIDENTIAL";
            else if (lns < 35) zoneType = "OFFICE";

            // 3. 업종별 시간대 적합도 매트릭스 계산 (0.0 ~ 1.0)
            let relevanceScore = 0.5; // 기본값
            if (job === "FB") { // F&B (식음료, 서빙) -> 점심, 저녁에 강세
                if (time === "noon" || time === "evening") relevanceScore = 0.95;
                else if (time === "afternoon") relevanceScore = 0.7;
                else relevanceScore = 0.4;
            } else if (job === "RETAIL") { // 편의점/마트 -> 아침, 저녁, 심야 골고루 적합
                if (time === "morning" || time === "evening" || time === "night") relevanceScore = 0.9;
                else relevanceScore = 0.6;
            } else if (job === "OFFICE") { // 사무 보조 -> 주중 아침/오후에 집중
                if (time === "morning" || time === "afternoon" || time === "noon") relevanceScore = 0.95;
                else relevanceScore = 0.3;
            } else if (job === "LOGISTICS") { // 배달/물류 -> 오후, 저녁, 심야 강세
                if (time === "evening" || time === "night" || time === "afternoon") relevanceScore = 0.95;
                else relevanceScore = 0.3;
            }

            // 4. 요일 패턴 가중치 (dayPatternWeight) 적용
            let dayPatternWeight = 1.0;
            if (zoneType === "OFFICE" && currentDay === "주말") {
                dayPatternWeight = 0.4; // 오피스 상권은 주말 구인 효율 극감
            } else if (zoneType === "CAMPUS_MIXED" && currentDay === "주말") {
                dayPatternWeight = 1.15; // 대학가/복합 상권은 주말에 추가 가산점
            } else if (zoneType === "RESIDENTIAL" && currentDay === "평일" && time === "morning") {
                dayPatternWeight = 1.1; // 주거 상권은 평일 아침 이탈 극대화 시점 가산점
            }

            // 5. 최종 점수 연산
            let rawScore = (trafficFactor * 40) + (relevanceScore * 50);
            let score = Math.round(rawScore * dayPatternWeight);
            score = Math.max(30, Math.min(99, score)); // 30 ~ 99점으로 정규화 보정

            // 6. 결과 리포트 값 매핑
            let days = "3일 이상";
            let applicants = "평균 수준";

            if (score >= 90) {
                days = "3시간 내";
                applicants = "평균 대비 3.2배";
            } else if (score >= 80) {
                days = "12시간 내";
                applicants = "평균 대비 2.1배";
            } else if (score >= 70) {
                days = "1일 내";
                applicants = "평균 대비 1.5배";
            } else if (score >= 50) {
                days = "2일 내";
                applicants = "평균 대비 1.1배";
            }

            return { score, days, applicants };
        }

        function runSimulation() {
            const placeholder = document.getElementById('sim-placeholder');
            const loading = document.getElementById('sim-loading');
            const results = document.getElementById('sim-results');

            placeholder.classList.add('hidden');
            loading.classList.remove('hidden');
            results.classList.add('hidden');

            setTimeout(() => {
                loading.classList.add('hidden');
                results.classList.remove('hidden');

                const simData = calculateSimulationScore();
                
                document.getElementById('sim-score-text').innerText = `${simData.score}점`;
                
                const evaluationText = document.getElementById('sim-evaluation');
                const progressBar = document.getElementById('sim-progress-bar');

                if (simData.score >= 90) {
                    evaluationText.innerText = "⚡ 최적 추천 (매우 높음)";
                    evaluationText.className = "text-[9px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200";
                    progressBar.className = "h-1.5 rounded-full bg-emerald-600 transition-all duration-700";
                } else if (simData.score >= 70) {
                    evaluationText.innerText = "👍 양호 (도달 가능)";
                    evaluationText.className = "text-[9px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200";
                    progressBar.className = "h-1.5 rounded-full bg-indigo-600 transition-all duration-700";
                } else {
                    evaluationText.innerText = "⚠️ 경고 (광고 낭비 우려)";
                    evaluationText.className = "text-[9px] font-semibold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200";
                    progressBar.className = "h-1.5 rounded-full bg-rose-500 transition-all duration-700";
                }

                progressBar.style.width = `${simData.score}%`;
                
                const jobName = document.getElementById('sim-job').options[document.getElementById('sim-job').selectedIndex].text.split(' ').slice(1).join(' ');
                const timeName = document.getElementById('sim-time').options[document.getElementById('sim-time').selectedIndex].text.split(' ').slice(1).join(' ');
                
                document.getElementById('sim-advice').innerText = `${currentStation}역 상권의 ${currentDay} 유동 분석 결과, [${timeName}] 시간대의 [${jobName}] 공고는 구인 확률 스코어 ${simData.score}점으로 산출되었습니다. 본 상권 피크 타임라인과의 매칭도가 높아 유료 광고비 대비 최적의 ROI를 보증합니다.`;
                document.getElementById('sim-days').innerText = simData.days;
                document.getElementById('sim-applicants').innerText = simData.applicants;
                
                refreshIcons();
            }, 300);
        }

        function focusTimelineZone(index) {
            if (selectedTimelineIndex === index) {
                selectedTimelineIndex = null;
            } else {
                selectedTimelineIndex = index;
            }
            
            if (chartInstance) {
                chartInstance.update();
            }
            
            openModal(index);
        }

        function openModal(index) {
            const currentData = rawDatabase[currentStation][currentDay];
            const peaks = getTop3Peaks(currentData);
            const proposal = getActionProposal(peaks[index], index, currentStation);
            
            const action = {
                time: `${["오전", "점심", "오후", "저녁", "야간"][index] || "시간대"} ${peaks[index].timeRange}`,
                title: proposal.title,
                desc: proposal.desc,
                tip: proposal.tip
            };

            const modal = document.getElementById('detail-modal');
            const innerModal = modal.querySelector('.transform');
            const badge = document.getElementById('modal-rank-badge');
            
            const ranks = ["🥇 1순위 제안 행동지침", "🥈 2순위 제안 행동지침", "🥉 3순위 제안 행동지침"];
            const colors = [
                "bg-red-50 text-red-700 border-red-200",
                "bg-orange-50 text-orange-700 border-orange-200",
                "bg-yellow-50 text-yellow-700 border-yellow-200"
            ];
            
            badge.innerText = ranks[index];
            badge.className = `text-[10px] font-extrabold px-2.5 py-1 rounded-full border ${colors[index]}`;
            
            document.getElementById('modal-time-badge').innerText = action.time;
            document.getElementById('modal-title').innerText = action.title;
            document.getElementById('modal-desc').innerHTML = action.desc;
            document.getElementById('modal-tip').innerText = action.tip;

            modal.classList.remove('hidden');
            setTimeout(() => {
                modal.classList.remove('opacity-0');
                innerModal.classList.remove('scale-95');
                innerModal.classList.add('scale-100');
            }, 50);
            
            refreshIcons();
        }

        function closeModal() {
            const modal = document.getElementById('detail-modal');
            const innerModal = modal.querySelector('.transform');
            
            modal.classList.add('opacity-0');
            innerModal.classList.remove('scale-100');
            innerModal.classList.add('scale-95');
            
            setTimeout(() => {
                modal.classList.add('hidden');
                selectedTimelineIndex = null;
                if (chartInstance) {
                    chartInstance.update();
                }
            }, 300);
        }

        function applyTimelineToSim() {
            const timeText = document.getElementById('modal-time-badge').innerText;
            const simTimeSelect = document.getElementById('sim-time');
            
            if (timeText.includes("07:00") || timeText.includes("08:00") || timeText.includes("09:00") || timeText.includes("10:00")) {
                simTimeSelect.value = "morning";
            } else if (timeText.includes("11:00") || timeText.includes("12:00") || timeText.includes("13:00")) {
                simTimeSelect.value = "noon";
            } else if (timeText.includes("14:00") || timeText.includes("15:00") || timeText.includes("16:00") || timeText.includes("17:00")) {
                simTimeSelect.value = "afternoon";
            } else if (timeText.includes("18:00") || timeText.includes("19:00") || timeText.includes("20:00")) {
                simTimeSelect.value = "evening";
            } else {
                simTimeSelect.value = "night";
            }
            
            closeModal();
            document.getElementById('sim-job').scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            const simSelectPanel = document.getElementById('sim-job').parentElement.parentElement;
            simSelectPanel.classList.add('ring-2', 'ring-indigo-500/30');
            setTimeout(() => {
                simSelectPanel.classList.remove('ring-2', 'ring-indigo-500/30');
            }, 1000);

            runSimulation();
        }

        function initStationDropdown() {
            const selectEl = document.getElementById('station-select');
            if (!selectEl) return;
            
            selectEl.innerHTML = '';
            
            const groups = {
                'RESIDENTIAL': { label: '🏠 주거 중심형 (Bed Town)', options: [] },
                'OFFICE': { label: '🏢 오피스 중심형 (Workplace)', options: [] },
                'CAMPUS_MIXED': { label: '🎨 지속 활성형 (Campus/Mixed)', options: [] }
            };
            
            for (const station in rawDatabase) {
                const currentData = rawDatabase[station]['평일'];
                if (!currentData || currentData.length < 20) continue;
                
                const morningSum = currentData[2] + currentData[3];
                const eveningSum = currentData[12] + currentData[13];
                const lateNightSum = currentData[16] + currentData[17];
                
                const pbi = morningSum > 0 ? (eveningSum / morningSum) : 0;
                const lns = eveningSum > 0 ? ((lateNightSum / eveningSum) * 100) : 0;
                
                let zoneType = "CAMPUS_MIXED";
                let suffix = " (복합상권)";
                if (pbi < 1.0) {
                    zoneType = "RESIDENTIAL";
                    suffix = " (주거밀집)";
                } else if (lns < 35) {
                    zoneType = "OFFICE";
                    suffix = " (오피스)";
                }
                
                groups[zoneType].options.push({
                    value: station,
                    text: `${station}역${suffix}`
                });
            }
            
            for (const key in groups) {
                groups[key].options.sort((a, b) => a.value.localeCompare(b.value, 'ko'));
            }
            
            const orderedKeys = ['RESIDENTIAL', 'OFFICE', 'CAMPUS_MIXED'];
            orderedKeys.forEach(key => {
                const group = groups[key];
                if (group.options.length === 0) return;
                
                const optgroupEl = document.createElement('optgroup');
                optgroupEl.label = group.label;
                
                group.options.forEach(opt => {
                    const optionEl = document.createElement('option');
                    optionEl.value = opt.value;
                    optionEl.textContent = opt.text;
                    optgroupEl.appendChild(optionEl);
                });
                
                selectEl.appendChild(optgroupEl);
            });
            
            if (rawDatabase['신림']) {
                selectEl.value = '신림';
                currentStation = '신림';
            } else {
                const firstStation = Object.keys(rawDatabase)[0];
                selectEl.value = firstStation;
                currentStation = firstStation;
            }
        }

        window.onload = function () {
            initStationDropdown();
            updateDashboard();
        };
    </script>
</body>
</html>
"""
# HTML 빌드 및 병합
final_html_content = html_base + js_template.replace("__RAW_DATABASE_PLACEHOLDER__", raw_db_js)

with open(HTML_FILE_PATH, mode='w', encoding='utf-8') as f:
    f.write(final_html_content)

print("4. index.html 복구 및 전체 역 데이터/동적 제안 연동 완료!")
