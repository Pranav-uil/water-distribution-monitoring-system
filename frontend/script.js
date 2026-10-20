// const API_URL = 'http://localhost:5000/data';
const API_URL = 'https://water-leakage-backend.onrender.com/data';
const nodeGrid = document.getElementById('node-grid');
const aiConfidenceEl = document.getElementById('ai-confidence');
const sysHealthEl = document.getElementById('sys-health');
const disconnectWarning = document.getElementById('disconnect-warning');
const statusIndicator = document.getElementById('status-indicator');
const alarmOverlay = document.getElementById('alarm-overlay');
const alarmText = document.getElementById('alarm-text');
const sirenAudio = document.getElementById('siren-audio');
const btnMute = document.getElementById('btn-mute');
const btnViewSystem = document.getElementById('view-system');
const btnViewNode = document.getElementById('view-node');


const nodeNames = "ABCDEFGHIJKLMNOPQ".split("");
let selectedNode = 'A';
let currentView = 'system'; 
let isMuted = false;
let alarmActive = false;
let nodeElements = {}; 


const MAX_DATA_POINTS = 20;
let chartTimeLabels = [];
let chartAvgData = [];
let chartSelectedNodeData = [];
let chartInstance = null;

// change
let demoModeActive = false;
let demoNodes = {};
const disconnectWarningDefaultText =
    disconnectWarning?.textContent?.trim() ||
    "LIVE TELEMETRY CONNECTION LOST";



function initUI() {
   
    nodeNames.forEach(nodeId => {
        const card = document.createElement('div');
        card.className = `node-card relative overflow-hidden bg-[#111] border border-gray-800 p-3 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 hover:border-cyan-500/50`;
        card.onclick = () => selectNode(nodeId);
        
        card.innerHTML = `
            <div class="text-xs text-gray-500 font-bold mb-1">NODE ${nodeId}</div>
            <div class="text-xl font-mono font-black text-white z-10 pressure-val" id="val-${nodeId}">--</div>
            <div class="text-[9px] text-gray-600 mt-1 z-10">PSI</div>
            <div class="absolute inset-0 bg-gradient-to-t from-cyan-900/20 to-transparent opacity-0 transition-opacity z-0" id="bg-${nodeId}"></div>
            <div class="absolute inset-0 border-2 border-red-500 opacity-0 pointer-events-none z-20" id="border-${nodeId}"></div>
        `;
        nodeGrid.appendChild(card);
        
      
        nodeElements[nodeId] = {
            card: card,
            val: document.getElementById(`val-${nodeId}`),
            bg: document.getElementById(`bg-${nodeId}`),
            border: document.getElementById(`border-${nodeId}`)
        };
    });

    
    // btnMute.addEventListener('click', () => {
    //     isMuted = !isMuted;
    //     if (isMuted) {
    //         sirenAudio.pause();
    //         btnMute.classList.replace('text-red-400', 'text-gray-500');
    //         btnMute.classList.replace('border-red-500', 'border-gray-600');
    //         btnMute.innerText = "AUDIO MUTED";
    //     } else {
    //         sirenAudio.play().catch(e => console.log("Audio play blocked by browser", e));
    //         btnMute.classList.replace('text-gray-500', 'text-red-400');
    //         btnMute.classList.replace('border-gray-600', 'border-red-500');
    //         btnMute.innerText = "MUTE AUDIO";
    //     }
    // });   

    btnMute.addEventListener('click', () => {
    isMuted = !isMuted;
    
    // Yeh line audio element ko internally mute/unmute karegi
    sirenAudio.muted = isMuted; 

    if (isMuted) {
        sirenAudio.pause(); 
        btnMute.classList.replace('text-red-400', 'text-gray-500');
        btnMute.classList.replace('border-red-500', 'border-gray-600');
        btnMute.innerText = "AUDIO MUTED";
    } else {
        // Agar pehle se alarm active hai, toh unmute karne par dubara play ho jaye
        if (alarmActive) {
            sirenAudio.play().catch(e => console.log("Audio play blocked by browser", e));
        }
        btnMute.classList.replace('text-gray-500', 'text-red-400');
        btnMute.classList.replace('border-gray-600', 'border-red-500');
        btnMute.innerText = "MUTE AUDIO";
    }
});

   
    btnViewSystem.addEventListener('click', () => setView('system'));
    btnViewNode.addEventListener('click', () => setView('node'));

    initChart();
    selectNode('A'); 
}

function initChart() {
    const ctx = document.getElementById('pressureChart').getContext('2d');
    
    
    Chart.defaults.color = '#555';
    Chart.defaults.font.family = 'monospace';

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartTimeLabels,
            datasets: [
                {
                    label: 'System Avg Pressure',
                    data: chartAvgData,
                    borderColor: '#00ffff',
                    backgroundColor: 'rgba(0, 255, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: `Node ${selectedNode} Pressure`,
                    data: chartSelectedNodeData,
                    borderColor: '#a855f7', 
                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0.3,
                    hidden: true 
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false, 
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    grid: { color: '#1a1a24', drawBorder: false }
                },
                y: {
                    grid: { color: '#1a1a24', drawBorder: false },
                    min: 0,
                    suggestedMax: 100
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#888', usePointStyle: true, boxWidth: 6 }
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#0ff',
                    bodyColor: '#fff',
                    borderColor: '#0ff',
                    borderWidth: 1
                }
            }
        }
    });
}



function selectNode(nodeId) {
    selectedNode = nodeId;
    
   
    for (const id in nodeElements) {
        if (id === nodeId) {
            nodeElements[id].card.classList.add('border-cyan-400');
            nodeElements[id].bg.classList.remove('opacity-0');
        } else {
            nodeElements[id].card.classList.remove('border-cyan-400');
            nodeElements[id].bg.classList.add('opacity-0');
        }
    }

   
    if (chartInstance) {
        chartInstance.data.datasets[1].label = `Node ${nodeId} Pressure`;
        chartInstance.update();
    }
}

function setView(view) {
    currentView = view;
    if (view === 'system') {
        btnViewSystem.className = "px-3 py-1 text-xs tracking-wider bg-cyan-900/40 text-cyan-400 transition-colors";
        btnViewNode.className = "px-3 py-1 text-xs tracking-wider text-gray-500 hover:text-cyan-400 transition-colors";
        
       
        chartInstance.setDatasetVisibility(0, true);
        chartInstance.setDatasetVisibility(1, false);
    } else {
        btnViewSystem.className = "px-3 py-1 text-xs tracking-wider text-gray-500 hover:text-cyan-400 transition-colors";
        btnViewNode.className = "px-3 py-1 text-xs tracking-wider bg-purple-900/40 text-purple-400 transition-colors";
        
        
        chartInstance.setDatasetVisibility(0, false);
        chartInstance.setDatasetVisibility(1, true);
    }
    chartInstance.update();
}


// change
function generateDemoData() {
    nodeNames.forEach((nodeId, index) => {
        if (demoNodes[nodeId] === undefined) {
            demoNodes[nodeId] = 104 + (index % 15);
        }

        // Simulated pressure variation for demonstration only
        demoNodes[nodeId] += (Math.random() - 0.5) * 2;
        demoNodes[nodeId] = Math.max(
            95,
            Math.min(125, demoNodes[nodeId])
        );
    });

    const values = Object.values(demoNodes);
    const avgPressure =
        values.reduce((sum, value) => sum + value, 0) /
        values.length;

    return {
        nodes: { ...demoNodes },
        avgPressure,
        ml_leaks: [],
        confidence: 94,
        health: 100,
        lastUpdated: Date.now()
    };
}

function showDemoMode() {
    demoModeActive = true;

    disconnectWarning.textContent =
        "DEMO MODE — SIMULATED DATA; LIVE TELEMETRY UNAVAILABLE";

    disconnectWarning.classList.remove("hidden");
    statusIndicator.classList.add("opacity-20");
}


// async function fetchTelemetry() {
//     try {
//         const res = await fetch(API_URL);
//         if (!res.ok) throw new Error("Network not ok");
//         const data = await res.json();
        
       
//         disconnectWarning.classList.add('hidden');
//         statusIndicator.classList.remove('opacity-20');
        
//         updateDashboard(data);
//     } catch (err) {
//         console.warn("Telemetry Connection Lost:", err);
//         disconnectWarning.classList.remove('hidden');
//         statusIndicator.classList.add('opacity-20');
//     }
// }

// new fetch telemetry()

async function fetchTelemetry() {
    try {
        const res = await fetch(API_URL, { cache: "no-store" });

        if (!res.ok) {
            throw new Error("Backend request failed");
        }

        const data = await res.json();

        // Render backend uses Date.now(), which is milliseconds.
        const timestamp = Number(data.lastUpdated);
        const updatedAt =
            timestamp > 0 && timestamp < 1e12
                ? timestamp * 1000
                : timestamp;

        const isStale =
            !updatedAt ||
            Date.now() - updatedAt > 10000;

        if (isStale) {
            showDemoMode();
            updateDashboard(generateDemoData());
            return;
        }

        // Fresh backend data: return to live mode.
        demoModeActive = false;

        disconnectWarning.textContent =
            disconnectWarningDefaultText;

        disconnectWarning.classList.add("hidden");
        statusIndicator.classList.remove("opacity-20");

        updateDashboard(data);

    } catch (err) {
        console.warn("Live telemetry unavailable:", err);

        showDemoMode();
        updateDashboard(generateDemoData());
    }
}


function updateDashboard(data) {
    if (!data || !data.nodes) return;

    
    aiConfidenceEl.innerText = `${data.confidence ?? '--'}%`;
    sysHealthEl.innerText = `${data.health ?? '--'}%`;

    
    if (data.health <= 50) {
        sysHealthEl.className = "text-xl font-bold text-red-500 text-shadow-red";
    } else if (data.health <= 80) {
        sysHealthEl.className = "text-xl font-bold text-yellow-400 text-shadow-yellow";
    } else {
        sysHealthEl.className = "text-xl font-bold text-green-400 text-shadow-green";
    }

   
    for (const [nodeId, value] of Object.entries(data.nodes)) {
        if (nodeElements[nodeId]) {
            const valClean = isNaN(value) ? 0 : parseFloat(value).toFixed(1);
            nodeElements[nodeId].val.innerText = valClean;

          
            nodeElements[nodeId].card.classList.remove('leak-alert');
            nodeElements[nodeId].border.classList.remove('animate-pulse', 'opacity-100');
            nodeElements[nodeId].val.classList.remove('text-red-500');
        }
    }

  
    const mlLeaks = Array.isArray(data.ml_leaks) ? data.ml_leaks : [];
    mlLeaks.forEach(leakNode => {
        if (nodeElements[leakNode]) {
            nodeElements[leakNode].card.classList.add('leak-alert');
            nodeElements[leakNode].border.classList.add('animate-pulse', 'opacity-100');
            nodeElements[leakNode].val.classList.add('text-red-500');
        }
    });

    

    
    if (mlLeaks.length > 0) {
        if (!alarmActive) {
            alarmOverlay.classList.remove('hidden');
            alarmActive = true;
            if (!isMuted) {
                sirenAudio.play().catch(e => console.log("Audio play blocked", e));
            }
        }
        alarmText.innerText = `LEAK DETECTED: NODE(S) ${mlLeaks.join(', ')}`;
    } else {
        if (alarmActive) {
            alarmOverlay.classList.add('hidden');
            alarmActive = false;
            sirenAudio.pause();
            sirenAudio.currentTime = 0; // reset audio
            
         
            // isMuted = false;
            // btnMute.classList.remove('text-gray-500', 'border-gray-600');
            // btnMute.classList.add('text-red-400', 'border-red-500');
            // btnMute.innerText = "MUTE AUDIO";
        }
    }

   
    updateChart(data);
}



function updateChart(data) {
    const now = new Date();
    const timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    
    const avgVal = isNaN(data.avgPressure) || data.avgPressure === null ? 0 : data.avgPressure;
    const selectedVal = data.nodes[selectedNode] !== undefined && !isNaN(data.nodes[selectedNode]) 
        ? data.nodes[selectedNode] 
        : 0;

    
    chartTimeLabels.push(timeString);
    chartAvgData.push(avgVal);
    chartSelectedNodeData.push(selectedVal);

    
    if (chartTimeLabels.length > MAX_DATA_POINTS) {
        chartTimeLabels.shift();
        chartAvgData.shift();
        chartSelectedNodeData.shift();
    }

   
    if (chartInstance) {
        chartInstance.update();
    }
}


document.addEventListener('DOMContentLoaded', () => {
    initUI();
    // Start Poll
    setInterval(fetchTelemetry, 1000);
});



