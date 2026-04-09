document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('generate-form');
  const btn = document.getElementById('generate-btn');
  const btnText = document.getElementById('btn-text');
  const btnSpinner = document.getElementById('btn-spinner');
  const msgBox = document.getElementById('status-message');
  const copyBtn = document.getElementById('copy-btn');
  const downloadBtn = document.getElementById('download-btn');
  
  const statSpec = document.getElementById('stat-spec');
  const statPy = document.getElementById('stat-python');
  const statJs = document.getElementById('stat-javascript');
  
  const metricRoutes = document.getElementById('metric-routes');
  const metricModels = document.getElementById('metric-models');
  
  const viewer = document.getElementById('spec-viewer');
  const placeholder = document.getElementById('code-placeholder');

  let currentSpecJSON = "";

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const filePath = document.getElementById('file-path').value;

    // UI Updating: Loading State
    btn.disabled = true;
    btnText.classList.add('hidden');
    btnSpinner.classList.remove('hidden');
    
    msgBox.className = 'status-msg hidden';
    msgBox.textContent = '';
    
    // Reset statuses
    [statSpec, statPy, statJs].forEach(el => {
      el.className = 'status-badge pending';
      el.textContent = 'Generating...';
    });
    
    let secondsElapsed = 0;
    placeholder.textContent = `Calling local LLM. This may take a minute... (0s elapsed)`;
    const timerInterval = setInterval(() => {
      secondsElapsed++;
      placeholder.textContent = `Calling local LLM. This may take a minute... (${secondsElapsed}s elapsed)`;
    }, 1000);

    viewer.innerHTML = '';
    currentSpecJSON = "";

    try {
      const response = await fetch('/generate-docs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        msgBox.className = 'status-msg success';
        msgBox.textContent = 'Documentation generated successfully!';
        
        statSpec.className = 'status-badge ok';
        statSpec.textContent = 'Created';
        
        statPy.className = data.sdk_results.python ? 'status-badge ok' : 'status-badge fail';
        statPy.textContent = data.sdk_results.python ? 'Generated' : 'Skipped';
        
        statJs.className = data.sdk_results.javascript ? 'status-badge ok' : 'status-badge fail';
        statJs.textContent = data.sdk_results.javascript ? 'Generated' : 'Skipped';
        
        metricRoutes.textContent = data.routes_found;
        metricModels.textContent = data.models_found;

        // Fetch the generated api.json directly to display
        fetchSpecFile();

      } else {
        msgBox.className = 'status-msg error';
        msgBox.textContent = data.message || 'Generation failed.';
        [statSpec, statPy, statJs].forEach(el => {
          el.className = 'status-badge fail';
          el.textContent = 'Failed';
        });
        placeholder.textContent = 'Failed to generate specs.';
      }
    } catch (err) {
      msgBox.className = 'status-msg error';
      msgBox.textContent = 'Network or server error occurred.';
      placeholder.textContent = 'Error fetching data.';
    } finally {
      clearInterval(timerInterval);
      // Re-enable button
      btn.disabled = false;
      btnSpinner.classList.add('hidden');
      btnText.classList.remove('hidden');
    }
  });

  async function fetchSpecFile() {
    try {
      // Small trick: since we don't have a direct endpoint serving the JSON statically,
      // and we want to view it, we can fetch it via /openapi.json which is fastapi's own.
      // Wait, our backend saves it to `spec/api.json`. We don't have an endpoint serving it!
      // I will fetch /openapi.json of the FASTAPI app as a fallback, 
      // or we can add a route to main.py to fetch the generated one. Mmm...
      // Let's just fetch the generated path if we can. 
      // Actually, since I'm going to update main.py next, I will add an endpoint: /generated-spec
      
      const res = await fetch('/generated-spec');
      if (res.ok) {
        const json = await res.json();
        currentSpecJSON = JSON.stringify(json, null, 2);
        
        viewer.textContent = currentSpecJSON;
        // Apply syntax highlighting
        hljs.highlightElement(viewer);
        placeholder.classList.add('hidden');
      } else {
        placeholder.textContent = 'Spec generated, but cannot load preview.';
      }
    } catch (e) {
      placeholder.textContent = 'Spec generated, but cannot load preview.';
    }
  }

  copyBtn.addEventListener('click', () => {
    if (!currentSpecJSON) return;
    navigator.clipboard.writeText(currentSpecJSON).then(() => {
      const originalText = copyBtn.textContent;
      copyBtn.textContent = 'Copied!';
      setTimeout(() => copyBtn.textContent = originalText, 2000);
    });
  });

  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      if (!currentSpecJSON) return;
      const blob = new Blob([currentSpecJSON], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'openapi-spec.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

});
