
require('dotenv').config();
const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 5000;


app.use(cors());
app.use(express.json());
     

let systemState = {   
  nodes: {},
  avgPressure: 0,
  ml_leaks: [],
  confidence: 95,
  health: 100,
  lastUpdated: null
};  


const nodeNames = "ABCDEFGHIJKLMNOPQ".split("");
nodeNames.forEach(n => systemState.nodes[n] = 0.0);


app.post('/api/pressure', (req, res) => {
  try {
    const { pressures, ml_leaks } = req.body;

    if (pressures && typeof pressures === 'object') {
      let totalPressure = 0;
      let nodeCount = 0;

    
      for (const [nodeId, value] of Object.entries(pressures)) {
        const numVal = parseFloat(value);
        if (!isNaN(numVal)) {
          systemState.nodes[nodeId] = numVal;
          totalPressure += numVal;
          nodeCount++;
        }
      }

     
      systemState.avgPressure = nodeCount > 0 ? (totalPressure / nodeCount) : 0;
    }

    if (Array.isArray(ml_leaks)) {
      systemState.ml_leaks = ml_leaks;
    } else {
      systemState.ml_leaks = [];
    }

   
    systemState.health = Math.max(0, 100 - (systemState.ml_leaks.length * 30));
    // Simulate slight fluctuation in AI confidence (85% to 99%)
    systemState.confidence = Math.floor(Math.random() * (99 - 85 + 1)) + 85;
    systemState.lastUpdated = Date.now();

    res.status(200).json({ status: "success", message: "Telemetry processed" });
  } catch (error) {
    console.error("Error processing telemetry:", error);
    res.status(500).json({ status: "error", message: "Internal server error" });
  }
});  

// GET Endpoint: Feeds Frontend Dashboard
app.get('/data', (req, res) => {
  res.status(200).json(systemState);
});


app.listen(PORT, () => {
  console.log(` SCADA Backend running on http://localhost:${PORT}`);
  console.log(` Ready to receive pipeline telemetry at POST /api/pressure`);
});


