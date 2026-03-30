import React, { useState, useRef } from 'react';
import axios from 'axios';
import { UploadCloud, CheckCircle, Loader2, AlertTriangle, ShieldCheck } from 'lucide-react';
import ModelViewer from './components/ModelViewer';

export default function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, processing, complete, error
  const [log, setLog] = useState([]);
  const [result, setResult] = useState(null);

  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  };

  const handleFile = (f) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setLog([]);
    setStatus('idle');
  };

  const runPipeline = async () => {
    if (!file) return;
    setStatus('processing');
    
    // Setup simulated log progress to give the user a cool "hacker" loading aesthetic
    // since the backend currently aggregates it all in one synchronous block.
    const steps = [
      "Uploading Blueprint...",
      "VLM Semantic Extraction...",
      "Deep Learning Wall Extraction...",
      "MIP Topological Optimization...",
      "3D Model Generation...",
      "Material Optimization...",
      "VLM Explainability...",
      "Soroban Web3 Logging..."
    ];
    
    let currentStep = 0;
    setLog([steps[0]]);
    const interval = setInterval(() => {
        currentStep++;
        if (currentStep < steps.length) {
            setLog(prev => [...prev, steps[currentStep]]);
        }
    }, 1500);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post('/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      clearInterval(interval);
      setLog(steps);
      setResult(res.data);
      setStatus('complete');
    } catch (err) {
      clearInterval(interval);
      console.error(err);
      setStatus('error');
      setLog(prev => [...prev, "Pipeline Error: " + err.message]);
    }
  };

  return (
    <div className="min-h-screen p-4 flex flex-col md:flex-row gap-6 bg-mesh">
      
      {/* LEFT PANEL: Uploader & Progress */}
      <div className="w-full md:w-1/4 flex flex-col gap-4">
        <h1 className="text-3xl font-bold gradient-text tracking-tighter mb-2">
          Structural<br/>Intelligence
        </h1>

        <div 
          className="glass-panel p-6 flex flex-col items-center justify-center border-2 border-dashed border-slate-600 hover:border-blue-500 transition-colors cursor-pointer relative"
          onDragOver={e => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-upload').click()}
        >
          <input 
            type="file" 
            id="file-upload" 
            className="hidden" 
            accept="image/*"
            onChange={(e) => { if(e.target.files[0]) handleFile(e.target.files[0]); }}
          />
          {preview ? (
            <img src={preview} alt="Plan" className="w-full h-auto rounded-lg mb-4 opacity-80" />
          ) : (
            <UploadCloud className="w-12 h-12 text-blue-400 mb-4" />
          )}
          <p className="text-sm text-slate-400 text-center font-medium">
            {file ? file.name : "Drag & Drop Floor Plan or Click to Browse"}
          </p>
        </div>

        <button 
          onClick={runPipeline}
          disabled={!file || status === 'processing'}
          className="glass-button w-full py-3 rounded-xl font-bold tracking-wide flex items-center justify-center gap-2 mt-2"
        >
          {status === 'processing' ? <Loader2 className="animate-spin" /> : 'Run Pipeline'}
        </button>

        <div className="glass-panel p-4 flex-1 overflow-y-auto custom-scrollbar">
          <h3 className="text-sm font-semibold text-slate-300 mb-3 border-b border-slate-700 pb-2">Pipeline Status</h3>
          <div className="flex flex-col gap-3">
            {log.map((entry, idx) => {
              const completed = (status === 'complete') || (idx < log.length - 1 && status === 'processing');
              const failed = status === 'error' && idx === log.length - 1;
              return (
                <div key={idx} className="flex items-center gap-3 text-sm">
                  {completed ? (
                    <span className="text-emerald-400"><CheckCircle size={16} /></span>
                  ) : failed ? (
                    <span className="text-red-500"><AlertTriangle size={16} /></span>
                  ) : (
                    <span className="text-blue-400"><Loader2 size={16} className="animate-spin" /></span>
                  )}
                  <span className={completed ? 'text-slate-200' : 'text-slate-400'}>{entry}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* CENTER PANEL: WebGL 3D Viewer */}
      <div className="w-full md:w-2/4 glass-panel relative p-1">
        <ModelViewer 
          segments={result?.geometry?.meshes || null} 
          openings={result?.geometry?.openings || null}
          floors={result?.geometry?.floors || null}
          furniture={result?.geometry?.furniture || null}
          labels={result?.geometry?.labels || null}
        />
        {status === 'processing' && (
          <div className="absolute inset-0 bg-black/40 rounded-xl flex items-center justify-center backdrop-blur-sm">
            <div className="flex flex-col items-center">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
              <p className="text-blue-200 font-mono tracking-widest text-glow animate-pulse">EXTRUDING TOPOLOGY</p>
            </div>
          </div>
        )}
      </div>

      {/* RIGHT PANEL: Insights & Web3 */}
      <div className="w-full md:w-1/4 flex flex-col gap-4">
        <div className="glass-panel p-5 flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-4">
          <h2 className="text-xl font-bold text-slate-200 border-b border-slate-700 pb-2 flex items-center justify-between">
            Engineering Insights
          </h2>
          
          {!result ? (
            <div className="text-slate-500 text-sm italic text-center mt-10">Upload a floorplan to begin analysis.</div>
          ) : (
            <>
              {/* Span Hard Constraints Banner */}
              {result.geometry?.metadata?.max_span_m > 5.0 && (
                <div className="bg-red-500/20 border-l-4 border-red-500 p-3 rounded-r-lg">
                  <h4 className="flex items-center gap-2 text-red-400 font-bold text-sm mb-1">
                    <AlertTriangle size={16}/> CRITICAL SPAN DETECTED
                  </h4>
                  <p className="text-xs text-red-200">
                    A span of {result.geometry.metadata.max_span_m}m was found. Materials &lt;30 MPa automatically disqualified.
                  </p>
                </div>
              )}

              {/* Material Explanations */}
              {result.explanations && Object.keys(result.explanations).map((key, i) => (
                <div key={i} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                  <h4 className="text-sm font-bold text-indigo-300 mb-2 uppercase tracking-wide flex items-center gap-2">
                    {key.replace(/_/g, ' ')}
                  </h4>
                  <p className="text-sm text-slate-300 leading-relaxed font-light">
                    {result.explanations[key]}
                  </p>
                </div>
              ))}
              
              {/* If no exact explanations dict from backend, render recommendations */}
              {!result.explanations && result.materials?.recommendations?.map((rec, i) => (
                  <div key={i} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                    <h4 className="text-sm font-bold text-blue-300 mb-1">{rec.element_label}</h4>
                    <p className="text-xs text-slate-400 mb-2">Span: {rec.span_m}m</p>
                    {rec.top_3_materials?.slice(0,1).map((mat, mIdx) => (
                        <div key={mIdx}>
                            <p className="text-sm text-emerald-400 font-bold mb-1">Winner: {mat.material_name}</p>
                            <p className="text-xs text-slate-300">{mat.strength_mpa} MPa | Cost: ₹{mat.cost_per_m3_inr}</p>
                            <p className="text-xs text-slate-400 font-light mt-2 italic">{mat.exclusion_reason || "Selected via WPM tradeoff scoring."}</p>
                        </div>
                    ))}
                  </div>
              ))}
            </>
          )}
        </div>

        {/* Soroban Badge Footer */}
        <div className="glass-panel p-4 bg-slate-900/60 flex items-center gap-3">
          <div className={`p-2 rounded-full ${result?.stellar_tx_hash ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-500'}`}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <h4 className={`text-sm font-bold ${result?.stellar_tx_hash ? 'text-emerald-400' : 'text-slate-400'}`}>
              {result?.stellar_tx_hash ? 'Secured on Stellar' : 'Blockchain Ledger'}
            </h4>
            {result?.stellar_tx_hash ? (
              <a 
                href={`https://stellar.expert/explorer/testnet/tx/${result.stellar_tx_hash}`}
                target="_blank" rel="noreferrer"
                className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-2 truncate block w-48"
              >
                Tx: {result.stellar_tx_hash.substring(0, 15)}...
              </a>
            ) : (
              <p className="text-xs text-slate-500">Awaiting Analysis...</p>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
