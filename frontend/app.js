class AutoPLCApp {
    init() {
        this.clientId = `client_${Math.random().toString(36).substr(2, 9)}`;
        this.websocket = null;
        this.currentTaskId = null;
        this.taskResult = null;
        this.simulationInterval = null;

        this.setupRouting();
        this.setupEventListeners();
        this.connectWebSocket();
        this.navigateTo('projects'); // Initial view
    }

    setupRouting() {
        this.views = {
            projects: document.getElementById('projects-view'),
            'project-detail': document.getElementById('project-detail-view'),
        };
        this.navLinks = document.querySelectorAll('.nav-link');

        this.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const viewName = e.target.getAttribute('data-view');
                this.navigateTo(viewName);
            });
        });
    }

    navigateTo(viewName, data = {}) {
        // Update nav links
        this.navLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('data-view') === viewName);
        });

        // Update views
        Object.values(this.views).forEach(view => {
            view.classList.remove('active');
        });
        this.views[viewName].classList.add('active');

        // Load data for the view
        switch (viewName) {
            case 'projects':
                this.loadProjectsData();
                break;
            case 'project-detail': this.loadProjectDetailView(data.taskId); break;
        }
    }

    setupEventListeners() {
        // Modal Handlers
        this.createProjectModal = document.getElementById('create-project-modal');
        document.getElementById('create-project-btn').addEventListener('click', () => this.createProjectModal.classList.add('active'));
        this.createProjectModal.querySelector('.modal-close-btn').addEventListener('click', () => this.createProjectModal.classList.remove('active'));
        document.getElementById('cancel-create-btn').addEventListener('click', () => this.createProjectModal.classList.remove('active'));

        // Form Submission
        const createForm = document.getElementById('create-project-form');
        createForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleCreateProject();
        });
        // Also handle direct click on the submit button as a fallback
        this.createProjectModal.querySelector('button[type="submit"]').addEventListener('click', () => this.handleCreateProject());
        
        document.getElementById('back-to-projects-btn').addEventListener('click', () => {
            this.navigateTo('projects');
        });

        // Event delegation for "View" buttons on projects table
        document.getElementById('projects-view').addEventListener('click', (e) => {
            const viewBtn = e.target.closest('.view-project-btn');
            const deleteBtn = e.target.closest('.delete-project-btn');

            if (viewBtn) {
                const taskId = viewBtn.dataset.taskId;
                this.navigateTo('project-detail', { taskId });
            } else if (deleteBtn) {
                const taskId = deleteBtn.dataset.taskId;
                this.handleDeleteProject(taskId);
            }
        });

        // New UI event listeners
        this.fullLogModal = document.getElementById('full-log-modal');
        document.getElementById('view-log-btn').addEventListener('click', () => this.fullLogModal.classList.add('active'));
        this.fullLogModal.querySelector('.modal-close-btn').addEventListener('click', () => this.fullLogModal.classList.remove('active'));

        // Add simulation modal handlers, but keep them safe in case buttons are missing
        this.simulationModal = document.getElementById('custom-simulation-modal');
        const simBtn = document.getElementById('simulate-btn');
        if (simBtn) simBtn.addEventListener('click', () => this.handleSimulateLogic());
        if (this.simulationModal) this.simulationModal.querySelector('.modal-close-btn').addEventListener('click', () => this.closeSimulationModal());
        document.getElementById('reset-simulation-btn')?.addEventListener('click', () => this.resetSimulation());
        
        document.getElementById('compile-btn')?.addEventListener('click', () => this.handleCompileCode());

        document.getElementById('copy-code-btn')?.addEventListener('click', () => this.handleCopyCode());
        document.getElementById('download-code-btn')?.addEventListener('click', () => this.handleDownloadCode());

        document.getElementById('feedback-form').addEventListener('submit', (e) => this.handleFeedbackSubmit(e));

    }

    // --- Data Loading & Rendering ---

    async loadProjectsData() {
        const container = document.getElementById('projects-table-container');
        container.innerHTML = '<p>Loading projects...</p>';

        try {
            const tasks = await apiService.getAllTasks();
            container.innerHTML = this.createProjectsTable(tasks);
        } catch (error) {
            container.innerHTML = '<p class="error">Failed to load projects.</p>';
            console.error(error);
        }
    }

    createProjectsTable(tasks) {
        if (!tasks || tasks.length === 0) {
            return '<p>No projects found. Create one to get started!</p>';
        }

        const rows = tasks.map(task => `
            <tr>
                <td>${task.prompt}</td>
                <td><span class="chip chip-${task.status.toLowerCase()}">${task.status}</span></td>
                <td>${task.quality_score ? task.quality_score.toFixed(1) : 'N/A'}</td>
                <td>${new Date(task.created_at).toLocaleString()}</td>
                <td>
                    <div class="table-actions">
                        <button class="btn-icon view-project-btn" title="View Project" data-task-id="${task.id}">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 12C1 12 5 4 12 4C19 4 23 12 23 12C23 12 19 20 12 20C5 20 1 12 1 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        </button>
                        <button class="btn-icon delete-project-btn" title="Delete Project" data-task-id="${task.id}">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle;">
                                <path d="M6 2H10M2 4H14M12.6667 4L12.1991 11.0129C12.129 12.065 12.0939 12.5911 11.8667 13.01C11.6666 13.3866 11.3648 13.6884 10.9882 13.8884C10.57 14.1156 10.0439 14.1507 9.00004 14.2208L7.00004 14.3641C5.95618 14.4342 5.43425 14.4693 5.01604 14.2421C4.63943 14.0421 4.33764 13.7403 4.1376 13.3637C3.91042 12.9455 3.87535 12.4236 3.80521 11.3797L3.33337 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        return `
            <table class="styled-table">
                <thead><tr><th>Prompt</th><th>Status</th><th>Score</th><th>Created</th><th>Actions</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    async loadProjectDetailView(taskId) {
        this.currentTaskId = taskId;
        this.taskResult = null;

        // Get new UI elements
        const chatHistory = document.getElementById('chat-history');
        const fullLogStream = document.getElementById('full-log-stream');
        const codeOutput = document.getElementById('code-output');
        const validationOutput = document.getElementById('validation-output');
        const projectTitle = document.getElementById('project-detail-title');

        // Reset UI
        this.resetAgentStatusUI();
        chatHistory.innerHTML = '<p>Loading project history...</p>';
        fullLogStream.innerHTML = '';
        codeOutput.innerHTML = '<pre><code>(* Waiting for agents... *)</code></pre>';
        validationOutput.innerHTML = '<p>Waiting for validation...</p>';
        projectTitle.textContent = `Project: ${taskId}`;
        this.setFeedbackFormState(false);
        document.getElementById('copy-code-btn').disabled = true;
        document.getElementById('download-code-btn').disabled = true;
        document.getElementById('compile-btn').disabled = true;
        document.getElementById('simulate-btn').disabled = true;

        // Subscribe to WebSocket updates for this task
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({ type: 'subscribe', task_id: taskId }));
        }

        try {
            const [messages, taskDetails] = await Promise.all([
                apiService.getTaskMessages(taskId),
                apiService.getTaskDetails(taskId)
            ]);

            projectTitle.textContent = taskDetails.prompt ? `Project: ${taskDetails.prompt.substring(0, 50)}...` : `Project: ${taskId}`;
            chatHistory.innerHTML = '';
            fullLogStream.innerHTML = '';
            messages.forEach(msg => this.renderAgentMessage(msg, true)); // Render to both logs

            if (taskDetails.status === 'completed' || taskDetails.status === 'failed') {
                this.taskResult = { success: taskDetails.status === 'completed', code: taskDetails.generated_code, validation_result: taskDetails.error_message || "Validation report not available." };
                this.renderCompletedResult(this.taskResult);
            }

        } catch (error) {
            chatHistory.innerHTML = '<p class="error">Could not load project history.</p>';
            console.error(error);
        }
    }
    
    async handleCreateProject() {
        const prompt = document.getElementById('project-prompt').value;
        if (!prompt) {
            alert('Project prompt cannot be empty.');
            return;
        }

        try {
            const result = await apiService.createTask({ prompt });
            this.createProjectModal.classList.remove('active');
            // Navigate directly to the new project's detail view
            this.navigateTo('project-detail', { taskId: result.task_id });
        } catch (error) {
            alert('Failed to create project.');
            console.error(error);
        }
    }

    async handleFeedbackSubmit(e) {
        e.preventDefault();
        const feedbackPrompt = document.getElementById('feedback-prompt');
        const feedback = feedbackPrompt.value.trim();
        if (!feedback) {
            alert('Feedback cannot be empty.');
            return;
        }

        this.setFeedbackFormState(false, 'Sending...');
        this.renderAgentMessage({ agent_role: 'User', content: feedback, timestamp: new Date().toISOString() }, true);

        try {
            await apiService.submitFeedback({ task_id: this.currentTaskId, feedback });
            feedbackPrompt.value = '';
            // The backend will now start a refinement process and send updates via WebSocket
        } catch (error) {
            alert(`Failed to submit feedback: ${error.message}`);
            this.setFeedbackFormState(true); // Re-enable on failure
        }
    }

    async handleCopyCode() {
        if (!this.taskResult || !this.taskResult.code) {
            alert('No code to copy.');
            return;
        }
        try {
            await navigator.clipboard.writeText(this.taskResult.code);
            alert('Code copied to clipboard!');
        } catch (err) {
            alert('Failed to copy code.');
            console.error('Copy failed', err);
        }
    }

    async handleDownloadCode() {
        if (!this.taskResult || !this.taskResult.code) {
            alert('No code to download.');
            return;
        }
        const blob = new Blob([this.taskResult.code], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `autoplc_project_${this.currentTaskId}.st`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async handleDeleteProject(taskId) {
        if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
            return;
        }
        try {
            await apiService.deleteTask(taskId);
            alert('Project deleted successfully.');
            this.loadProjectsData(); // Refresh the list
        } catch (error) {
            alert(`Failed to delete project: ${error.message}`);
        }
    }

    async handleCompileCode() {
        if (!this.taskResult || !this.taskResult.code) {
            alert('No code available to compile.');
            return;
        }
        const compileBtn = document.getElementById('compile-btn');
        compileBtn.textContent = 'Compiling...';
        compileBtn.disabled = true;

        try {
            const result = await apiService.compileCode({ code: this.taskResult.code });
            alert(result.message);
        } catch (error) {
            alert(`Compilation request failed: ${error.message}`);
        } finally {
            compileBtn.textContent = 'Compile';
            compileBtn.disabled = false;
        }
    }

    async handleSimulateLogic() {
        if (!this.taskResult || !this.taskResult.code) {
            alert('No code available to simulate.');
            return;
        }

        try {
            // Fetch task details to get the original prompt for context
            const taskDetails = await apiService.getTaskDetails(this.currentTaskId);
            if (!taskDetails || !taskDetails.prompt) {
                alert('Could not retrieve original prompt for simulation context.');
                return;
            }

            const dashboardData = await apiService.generateDashboard({ 
                code: this.taskResult.code,
                prompt: taskDetails.prompt
            });

            if (!dashboardData.success) {
                alert(`Failed to generate simulation dashboard from code: ${dashboardData.error}`);
                return;
            }

            const dashboardDef = dashboardData.dashboard;
            
            // Extract inputs and outputs for the interpreter from the LLM-generated definition
            const inputs = dashboardDef.components
                .filter(c => c.group === 'inputs')
                .map(c => ({ name: c.variable }));
            
            const outputs = dashboardDef.components
                .filter(c => c.group === 'outputs')
                .map(c => ({ name: c.variable }));

            this.openSimulationModal(inputs, outputs, dashboardDef);

        } catch (error) {
            alert(`Failed to start simulation: ${error.message}`);
        }
    }

    openSimulationModal(inputs, outputs, dashboardDef) {
        this.simulationState = {
            variables: {},
            timeline: [],
            timelineCounter: 0,
            inputs: inputs,
            outputs: outputs,
            momentaryInputs: new Set() // Add this for momentary buttons
        };
        this.buildSimulatorUIFromDef(dashboardDef);
        this.simulationModal.classList.add('active');
        this.startSimulation(inputs, outputs);
    }

    parseAllVariablesFromCode(code) {
        const varBlockMatch = code.match(/VAR\s*([\s\S]*?)\s*END_VAR/i);
        if (!varBlockMatch) return [];
    
        const varBlock = varBlockMatch[1];
        const varRegex = /(\w+)\s*:/g;
        const variables = new Set();
        let match;
        while ((match = varRegex.exec(varBlock)) !== null) {
            variables.add(match[1]);
        }
        return Array.from(variables);
    }
    
    buildSimulatorUIFromDef(dashboardDef) {
        const inputsContainer = document.getElementById('sim-inputs-container');
        const outputsContainer = document.getElementById('sim-outputs-container');
        const simTitle = this.simulationModal.querySelector('h2');

        if (simTitle) {
            simTitle.textContent = dashboardDef.title || 'Logic Simulator';
        }
        
        inputsContainer.innerHTML = '';
        outputsContainer.innerHTML = '';

        dashboardDef.components.forEach(component => {
            let componentHtml = '';
            switch(component.type) {
                case 'momentary_button':
                    componentHtml = `
                        <div class="io-indicator" id="sim-indicator-${component.variable}"></div>
                        <span>${component.label}</span>
                        <button class="io-button" data-var-name="${component.variable}">Press</button>
                    `;
                    break;
                case 'toggle_switch':
                    componentHtml = `
                        <div class="io-indicator" id="sim-indicator-${component.variable}"></div>
                        <span>${component.label}</span>
                        <button class="io-button" data-var-name="${component.variable}" data-sim-type="toggle">Toggle</button>
                    `;
                    break;
                case 'indicator_light':
                    componentHtml = `
                        <div class="io-indicator output" id="sim-indicator-${component.variable}"></div>
                        <span>${component.label}</span>
                        <span class="status-text off" id="sim-status-${component.variable}">OFF</span>
                    `;
                    break;
                case 'display_value':
                     componentHtml = `
                        <span>${component.label}</span>
                        <span class="status-text" id="sim-status-${component.variable}">0</span>
                    `;
                    break;
            }

            const item = document.createElement('div');
            item.className = 'io-item';
            item.innerHTML = componentHtml;

            if (component.group === 'inputs') {
                inputsContainer.appendChild(item);
            } else if (component.group === 'outputs') {
                outputsContainer.appendChild(item);
            }
        });
        
        // Add event listeners to new buttons
        inputsContainer.querySelectorAll('.io-button').forEach(button => {
            button.addEventListener('click', () => {
                const varName = button.dataset.varName;
                const simType = button.dataset.simType;
                if (simType === 'toggle') {
                    this.toggleSwitch(varName);
                } else {
                    this.toggleInput(varName); // This is the momentary press
                }
            });
        });
    }


    toggleInput(varName) {
        const variableKey = varName.toUpperCase();
        const variable = this.simulationState.variables[variableKey];
        if (typeof variable === 'undefined' || typeof variable !== 'boolean') return;
    
        // If a press is already in progress, do nothing
        if (this.simulationState.variables[variableKey] === true) return;
    
        // Simulate a momentary button press
        this.simulationState.variables[variableKey] = true;
        this.addTimelineEvent(`Input '${varName}' Pressed`, 'Input Active');
        const indicator = document.getElementById(`sim-indicator-${varName}`);
        if (indicator) indicator.classList.add('active');
    
        // Flag this input to be reset after the next simulation cycle
        this.simulationState.momentaryInputs.add(variableKey);
    }
    
    toggleSwitch(varName) {
        const variableKey = varName.toUpperCase();
        const currentState = this.simulationState.variables[variableKey];
        const newState = !currentState;
        this.simulationState.variables[variableKey] = newState;
        
        this.addTimelineEvent(`Input '${varName}' Toggled`, `State is now ${newState ? 'ON' : 'OFF'}`);
        const indicator = document.getElementById(`sim-indicator-${varName}`);
        if (indicator) indicator.classList.toggle('active', newState);
    }

    startSimulation(inputs, outputs) {
      if (this.simulationInterval) {
          clearInterval(this.simulationInterval);
      }
      
      const allVars = this.parseAllVariablesFromCode(this.taskResult.code);
      
      this.simulationState.variables = allVars.reduce((acc, name) => {
          acc[name.toUpperCase()] = false; // Default all to false
          return acc;
      }, {});

      let lastOutputState = {};

      // Use a longer interval for LLM calls
      this.simulationInterval = setInterval(async () => {
          try {
              const stateToSend = { ...this.simulationState.variables };
  
              const response = await apiService.simulationStep({
                  code: this.taskResult.code,
                  current_state: stateToSend
              });
  
              // After the API call, reset momentary inputs that were active for this cycle
              if (this.simulationState.momentaryInputs.size > 0) {
                  this.simulationState.momentaryInputs.forEach(key => {
                      this.simulationState.variables[key] = false;
                      // Find original case for ID
                      const varName = allVars.find(v => v.toUpperCase() === key);
                      if (varName) {
                          const indicator = document.getElementById(`sim-indicator-${varName}`);
                          if (indicator) indicator.classList.remove('active');
                      }
                  });
                  this.simulationState.momentaryInputs.clear();
              }
  
              if (response.success) {
                  // Backend returns uppercase keys, which matches our internal state
                  this.simulationState.variables = response.new_state;
              } else {
                  console.error("Simulation step failed:", response.error);
                  this.addTimelineEvent('Simulation Error', response.error.substring(0, 100) + '...');
                  clearInterval(this.simulationInterval);
                  this.simulationInterval = null;
                  return;
              }
  
              // Update UI based on the new state
              outputs.forEach(output => {
                  const varName = output.name.toUpperCase();
                  const indicator = document.getElementById(`sim-indicator-${output.name}`);
                  const statusText = document.getElementById(`sim-status-${output.name}`);
                  const currentValue = this.simulationState.variables[varName];
  
                  if (statusText && typeof currentValue !== 'boolean') {
                      statusText.textContent = currentValue;
                      if (indicator) indicator.classList.toggle('active', currentValue > 0);
                  } else {
                      const isNowActive = !!currentValue;
                      if (indicator) indicator.classList.toggle('active', isNowActive);
                      if (statusText) {
                          statusText.textContent = isNowActive ? 'ON' : 'OFF';
                          statusText.className = `status-text ${isNowActive ? 'on' : 'off'}`;
                      }
                  }
  
                  if (lastOutputState[varName] !== currentValue) {
                      this.addTimelineEvent(`Output '${output.name}' Changed`, `State is now ${currentValue}`);
                  }
                  lastOutputState[varName] = currentValue;
              });
  
          } catch (error) {
              console.error("API call for simulation step failed:", error);
              this.addTimelineEvent('API Error', error.message);
              clearInterval(this.simulationInterval);
              this.simulationInterval = null;
          }
      }, 1000); // 1 second interval
    }

    addTimelineEvent(event, state) {
        const timelineContainer = document.getElementById('sim-timeline-container');
        if (!timelineContainer) return;

        // Deactivate previous item
        const lastActive = timelineContainer.querySelector('.timeline-item.active');
        if (lastActive) lastActive.classList.remove('active');

        const timelineItem = document.createElement('div');
        timelineItem.className = 'timeline-item active';
        
        this.simulationState.timelineCounter += 0.2; // Corresponds to 200ms interval
        const timeString = `T+${this.simulationState.timelineCounter.toFixed(1)}s`;
        
        timelineItem.innerHTML = `
            <div class="timeline-marker"></div>
            <div class="timeline-content">
                <strong>${timeString}:</strong> ${event} &mdash; ${state}
            </div>
        `;
        
        timelineContainer.appendChild(timelineItem);
        timelineContainer.scrollTop = timelineContainer.scrollHeight;
    }

    resetSimulation() {
        // Reset timeline UI and counter
        const timelineContainer = document.getElementById('sim-timeline-container');
        if (timelineContainer) {
            timelineContainer.innerHTML = `
                <div class="timeline-item active">
                    <div class="timeline-marker"></div>
                    <div class="timeline-content">
                        <strong>T+0s:</strong> Simulation Reset.
                    </div>
                </div>
            `;
        }
        this.simulationState.timelineCounter = 0;

        // Restart the simulation loop. startJsSimulation handles clearing the old interval and resetting variables.
        this.startSimulation(this.simulationState.inputs, this.simulationState.outputs);
    }

    closeSimulationModal() {
        if (this.simulationInterval) {
            clearInterval(this.simulationInterval);
            this.simulationInterval = null;
        }
        this.simulationModal.classList.remove('active');
    }

    // --- WebSocket Handling ---

    connectWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws/${this.clientId}`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('🔌 WebSocket connected.');
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.websocket.onclose = () => {
            console.log('🔌 WebSocket disconnected. Reconnecting in 3s...');
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleWebSocketMessage(data) {
        console.log('📨 WebSocket message:', data);

        // Ignore messages for other tasks
        if (data.task_id && this.currentTaskId && data.task_id !== this.currentTaskId) {
            return;
        }

        // Handle initial status and progress updates
        if (data.type === 'status_update' || data.type === 'progress' || data.type === 'agent_update') {
            if (data.agent) this.updateAgentStatusUI(data.agent, data.status);
            this.renderAgentMessage({
                agent_role: data.agent || 'Supervisor',
                content: data.message,
                timestamp: data.timestamp,
            }, true);
        } else if (data.type === 'completed') {
            this.renderAgentMessage({
                agent_role: 'Supervisor',
                content: 'Workflow completed!',
                timestamp: data.timestamp,
            }, true);
            this.taskResult = data.result; // Store the result
            this.renderCompletedResult(this.taskResult);
        } else if (data.type === 'feedback_processed') {
            this.renderAgentMessage({ agent_role: 'Supervisor', content: 'Feedback processed. New code generated.', timestamp: data.timestamp }, true);
            this.taskResult = data.result;
            this.renderCompletedResult(this.taskResult);
        } else if (data.type === 'error') {
            this.renderAgentMessage({
                agent_role: 'Supervisor',
                content: `Error: ${data.error}`,
                timestamp: data.timestamp,
            }, true);
            this.setFeedbackFormState(true);
        }
    }

    renderCompletedResult(result) {
        const codeOutput = document.getElementById('code-output');
        const validationOutput = document.getElementById('validation-output');

        codeOutput.innerHTML = `<pre><code>${result.code || "Code not generated."}</code></pre>`;

        const success = result.success || (result.validation_result && result.validation_result.includes("VALIDATION PASSED"));
        const hasCode = result.code && result.code.trim().length > 0;
        
        if (success) {
            validationOutput.innerHTML = `<pre>${result.validation_result || "Validation passed, but no report was generated."}</pre>`;
        } else {
            validationOutput.innerHTML = '<p>Validation failed. Check the "View Full Agent Log" for details.</p>';
        }

        const simBtn = document.getElementById('simulate-btn'); // This is now the JS sim button
        if (simBtn) {
            simBtn.disabled = !hasCode;
        }

        document.getElementById('copy-code-btn').disabled = !hasCode;
        document.getElementById('download-code-btn').disabled = !hasCode;

        this.setFeedbackFormState(true);
    }

    renderAgentMessage(msg, renderToBoth = false) {
        const chatHistory = document.getElementById('chat-history');
        const fullLogStream = document.getElementById('full-log-stream');

        // Create a summary for long messages or code blocks for the main chat view
        let summaryContent = msg.content;
        const fullContent = msg.content.replace(/\n/g, '<br>'); // Keep full content for the log modal

        if (summaryContent.length > 300 || summaryContent.includes('PROGRAM')) {
            const firstLine = summaryContent.split('\n')[0];
            summaryContent = `${firstLine.substring(0, 100)}... <br><i>(Full content in "View Full Agent Log")</i>`;
        }
        summaryContent = summaryContent.replace(/\n/g, '<br>');

        const createMessageHTML = (content) => `
            <div>
                <span class="agent-name">${msg.agent_role || 'User'}</span>
                <span class="timestamp">${new Date(msg.timestamp).toLocaleTimeString()}</span>
            </div>
            <div>${content}</div>
        `;

        // Render to the main chat history (simplified view)
        const summaryMessageEl = document.createElement('div');
        summaryMessageEl.classList.add('log-message');
        summaryMessageEl.innerHTML = createMessageHTML(summaryContent);
        chatHistory.appendChild(summaryMessageEl);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        // Render to the full log modal
        if (renderToBoth) {
            const fullMessageEl = document.createElement('div');
            fullMessageEl.classList.add('log-message');
            fullMessageEl.innerHTML = createMessageHTML(fullContent);
            fullLogStream.appendChild(fullMessageEl);
            fullLogStream.scrollTop = fullLogStream.scrollHeight;
        }
    }

    setFeedbackFormState(enabled, buttonText = 'Send Feedback') {
        document.getElementById('feedback-prompt').disabled = !enabled;
        const feedbackBtn = document.getElementById('feedback-submit-btn');
        feedbackBtn.disabled = !enabled;
        feedbackBtn.textContent = buttonText;
    }

    resetAgentStatusUI() {
        const agentItems = document.querySelectorAll('.agent-status-item');
        agentItems.forEach(item => item.className = 'agent-status-item');
    }

    updateAgentStatusUI(agentName, status) { // agentName is lowercase
        const agentItem = document.querySelector(`.agent-status-item[data-agent="${agentName}"]`);
        if (!agentItem) return;

        // When a new agent becomes active, mark the previous one as completed.
        if (status === 'active') {
            const currentActive = document.querySelector('.agent-status-item.active');
            if (currentActive && currentActive !== agentItem) {
                currentActive.classList.remove('active');
                currentActive.classList.add('completed');
            }
        }

        // Set the status for the current agent
        agentItem.classList.remove('active', 'completed', 'error');
        agentItem.classList.add(status);
    }
}

// --- API Service Layer ---
// This maps to the FastAPI backend endpoints.

const apiService = {    
    getAllTasks: async () => {
        const response = await fetch('/api/tasks');
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    },

    createTask: async (data) => {
        // Your backend uses `/api/generate` to create a new task
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    },
    
    getTaskDetails: async (taskId) => {
        const response = await fetch(`/api/tasks/${taskId}`);
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    },

    getTaskMessages: async (taskId) => {
        const response = await fetch(`/api/tasks/${taskId}/messages`);
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    },

    submitFeedback: async (data) => {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to submit feedback');
        }
        return response.json();
    },

    deleteTask: async (taskId) => {
        const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to delete task');
        }
        return response.json();
    },

    compileCode: async (data) => {
        const response = await fetch('/api/compile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to compile code');
        }
        return response.json();
    },
    parseVariables: async (data) => {
        const response = await fetch('/api/parse-variables', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('Failed to parse variables');
        return response.json();
    }
    ,
    generateDashboard: async (data) => {
        const response = await fetch('/api/simulation/dashboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to generate dashboard');
        }
        return response.json();
    },
    simulationStep: async (data) => {
        const response = await fetch('/api/simulation/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to run simulation step');
        }
        return response.json();
    },
};

document.addEventListener('DOMContentLoaded', () => {
    const app = new AutoPLCApp();
    app.init();
});
