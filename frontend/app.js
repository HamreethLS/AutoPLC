// frontend/app.js - Complete JavaScript functionality

class AutoPLCApp {
    constructor() {
        this.currentTaskId = null;
        this.statusInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateCharCount();
        this.loadTaskHistory();
        this.checkSystemStatus();
    }

    bindEvents() {
        // Input events
        const promptInput = document.getElementById('promptInput');
        const generateBtn = document.getElementById('generateBtn');
        
        promptInput.addEventListener('input', () => {
            this.updateCharCount();
            this.updateGenerateButton();
        });
        
        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this.generateCode();
            }
        });

        // Button events
        generateBtn.addEventListener('click', () => this.generateCode());
        document.getElementById('copyCodeBtn').addEventListener('click', () => this.copyCode());
        document.getElementById('simulateBtn').addEventListener('click', () => this.showSimulationModal());
        document.getElementById('downloadBtn').addEventListener('click', () => this.downloadCode());
        document.getElementById('newChatBtn').addEventListener('click', () => this.newChat());
        document.getElementById('systemInfoBtn').addEventListener('click', () => this.showSystemInfo());

        // Modal events
        document.getElementById('closeModalBtn').addEventListener('click', () => this.closeModal('systemInfoModal'));
        document.getElementById('closeSimModalBtn').addEventListener('click', () => this.closeModal('simulationModal'));
        
        // Simulation controls
        document.getElementById('startSimBtn').addEventListener('click', () => this.startSimulation());
        document.getElementById('stopSimBtn').addEventListener('click', () => this.stopSimulation());
        document.getElementById('refreshSimBtn').addEventListener('click', () => this.refreshSimulationStatus());

        // Close modals on background click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target.id);
            }
        });
    }

    updateCharCount() {
        const promptInput = document.getElementById('promptInput');
        const charCount = document.getElementById('charCount');
        const count = promptInput.value.length;
        charCount.textContent = `${count}/1000`;
        
        if (count > 900) {
            charCount.style.color = 'var(--danger-color)';
        } else if (count > 750) {
            charCount.style.color = 'var(--warning-color)';
        } else {
            charCount.style.color = 'var(--text-secondary)';
        }
    }

    updateGenerateButton() {
        const promptInput = document.getElementById('promptInput');
        const generateBtn = document.getElementById('generateBtn');
        const isValid = promptInput.value.trim().length > 0;
        generateBtn.disabled = !isValid;
    }

    async generateCode() {
        const promptInput = document.getElementById('promptInput');
        const generateBtn = document.getElementById('generateBtn');
        const prompt = promptInput.value.trim();

        if (!prompt) {
            this.showNotification('Please enter a description for your PLC system', 'error');
            return;
        }

        // Update UI for loading state
        generateBtn.querySelector('.btn-text').style.display = 'none';
        generateBtn.querySelector('.btn-loading').style.display = 'flex';
        generateBtn.disabled = true;

        this.updateStatus('🔄 Generating', 'Starting multi-agent code generation...');

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.currentTaskId = data.task_id;

            // Add user message to chat
            this.addMessageToChat('user', 'You', prompt);
            
            // Start polling for status
            this.startStatusPolling();

        } catch (error) {
            console.error('Generation error:', error);
            this.showNotification('Failed to start code generation. Please try again.', 'error');
            this.resetGenerateButton();
        }
    }

    startStatusPolling() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
        }

        this.statusInterval = setInterval(async () => {
            if (this.currentTaskId) {
                await this.checkTaskStatus();
            }
        }, 1000);
    }

    async checkTaskStatus() {
        try {
            const response = await fetch(`/api/status/${this.currentTaskId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                this.handleTaskCompletion(data);
            } else if (data.status === 'failed') {
                this.handleTaskFailure(data);
            } else {
                // Update status
                const agent = data.current_agent || 'Working';
                const runtime = data.runtime_seconds || 0;
                this.updateStatus(`🤖 ${agent}`, `Runtime: ${runtime}s | Messages: ${data.message_count || 0}`);
            }
        } catch (error) {
            console.error('Status check error:', error);
        }
    }

    handleTaskCompletion(data) {
        clearInterval(this.statusInterval);
        this.resetGenerateButton();

        const result = data.result;
        
        if (result.success) {
            // Show generated code
            this.displayGeneratedCode(result.generated_code, result);
            
            // Add agent messages to chat
            if (result.history) {
                result.history.forEach(msg => {
                    this.addMessageToChat('agent', msg.role, msg.content);
                });
            }

            this.updateStatus('✅ Complete', `Generated code successfully! Quality: ${(result.quality_score || 0).toFixed(1)}/2.0`);
            this.showNotification('Code generated successfully!', 'success');
        } else {
            this.updateStatus('⚠️ Issues', 'Code generated but may have issues');
            this.displayGeneratedCode(result.generated_code, result);
            this.showNotification('Code generated with warnings. Check the output.', 'warning');
        }

        // Update task history
        this.loadTaskHistory();
    }

    handleTaskFailure(data) {
        clearInterval(this.statusInterval);
        this.resetGenerateButton();
        
        this.updateStatus('❌ Failed', 'Code generation failed');
        this.showNotification(`Generation failed: ${data.error || 'Unknown error'}`, 'error');
    }

    displayGeneratedCode(code, result) {
        const codeElement = document.getElementById('generatedCode');
        const codeStats = document.getElementById('codeStats');
        
        codeElement.textContent = code;
        
        // Update stats
        const stats = [
            `Quality Score: ${(result.quality_score || 0).toFixed(1)}/2.0`,
            `Lines: ${code.split('\n').length}`,
            `Characters: ${code.length}`,
            `Compiler: ${result.compiler_result?.includes('Successful') ? '✅ Pass' : '❌ Fail'}`,
            `Linter: ${result.linter_result?.includes('Passed') ? '✅ Pass' : '⚠️ Warnings'}`
        ];
        
        codeStats.innerHTML = stats.join(' | ');
    }

    addMessageToChat(type, role, content) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <div class="agent-avatar agent-${role.toLowerCase().replace(/[^a-z]/g, '')}">${role.charAt(0)}</div>
                <span class="agent-name">${role}</span>
                <span class="message-timestamp">${timestamp}</span>
            </div>
            <div class="message-content">
                ${this.formatMessageContent(content)}
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    formatMessageContent(content) {
        // Basic formatting for code blocks and links
        return content
            .replace(/``````/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    resetGenerateButton() {
        const generateBtn = document.getElementById('generateBtn');
        generateBtn.querySelector('.btn-text').style.display = 'inline';
        generateBtn.querySelector('.btn-loading').style.display = 'none';
        generateBtn.disabled = false;
        this.updateGenerateButton();
    }

    updateStatus(indicator, text) {
        document.getElementById('statusIndicator').textContent = indicator;
        document.getElementById('statusText').textContent = text;
    }

    async copyCode() {
        const code = document.getElementById('generatedCode').textContent;
        try {
            await navigator.clipboard.writeText(code);
            this.showNotification('Code copied to clipboard!', 'success');
        } catch (error) {
            this.showNotification('Failed to copy code', 'error');
        }
    }

    downloadCode() {
        const code = document.getElementById('generatedCode').textContent;
        const blob = new Blob([code], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `plc_program_${Date.now()}.st`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Code downloaded!', 'success');
    }

    newChat() {
        // Clear current task
        this.currentTaskId = null;
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
        }

        // Clear chat messages
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-content">
                    <h2>🤖 Welcome to AutoPLC Enhanced</h2>
                    <p>AI-powered Structured Text generation with multi-agent collaboration</p>
                    <div class="feature-highlights">
                        <div class="feature">
                            <span class="feature-icon">🧠</span>
                            <span>NVIDIA NIM Multi-Model Routing</span>
                        </div>
                        <div class="feature">
                            <span class="feature-icon">⚡</span>
                            <span>Real-time Agent Collaboration</span>
                        </div>
                        <div class="feature">
                            <span class="feature-icon">✅</span>
                            <span>Syntax Validation & Simulation</span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Clear input and code
        document.getElementById('promptInput').value = '';
        document.getElementById('generatedCode').textContent = '(* Generated code will appear here *)';
        document.getElementById('codeStats').innerHTML = '';
        
        // Reset status
        this.updateStatus('🟢 Ready', 'AutoPLC Enhanced - Ready for code generation');
        this.updateCharCount();
        this.updateGenerateButton();
    }

    async showSystemInfo() {
        const modal = document.getElementById('systemInfoModal');
        const content = document.getElementById('systemInfoContent');
        
        content.innerHTML = 'Loading system information...';
        modal.classList.add('active');

        try {
            const response = await fetch('/api/system/info');
            const data = await response.json();
            
            content.innerHTML = `
                <div class="system-info">
                    <h4>System Status: ${data.system_status}</h4>
                    <p><strong>Knowledge Base:</strong> ${data.knowledge_base?.document_count || 0} documents loaded</p>
                    <p><strong>Compiler:</strong> ${data.compiler?.status || 'Unknown'}</p>
                    <p><strong>Active Tasks:</strong> ${data.active_tasks || 0}</p>
                    <p><strong>Total Tasks:</strong> ${data.total_tasks || 0}</p>
                    <p><strong>Dual-Key Mode:</strong> ${data.dual_key_enabled ? 'Enabled ✅' : 'Disabled ⚠️'}</p>
                    
                    <h4>API Keys:</h4>
                    <p>Primary: ${data.api_keys?.nvidia_primary || 'Not configured'}</p>
                    <p>Secondary: ${data.api_keys?.nvidia_secondary || 'Not configured'}</p>
                    <p>Tavily: ${data.api_keys?.tavily || 'Not configured'}</p>
                </div>
            `;
        } catch (error) {
            content.innerHTML = `<p class="error-state">Failed to load system information: ${error.message}</p>`;
        }
    }

    async showSimulationModal() {
        const modal = document.getElementById('simulationModal');
        modal.classList.add('active');
        this.refreshSimulationStatus();
    }

    async startSimulation() {
        const code = document.getElementById('generatedCode').textContent;
        
        if (!code || code === '(* Generated code will appear here *)') {
            this.showNotification('No code to simulate', 'error');
            return;
        }

        try {
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Simulation started!', 'success');
                this.refreshSimulationStatus();
            } else {
                this.showNotification(`Simulation failed: ${data.message}`, 'error');
            }
        } catch (error) {
            this.showNotification('Simulation error', 'error');
        }
    }

    async stopSimulation() {
        try {
            const response = await fetch('/api/simulation/stop', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Simulation stopped', 'success');
                this.refreshSimulationStatus();
            }
        } catch (error) {
            this.showNotification('Failed to stop simulation', 'error');
        }
    }

    async refreshSimulationStatus() {
        try {
            const response = await fetch('/api/simulation/status');
            const data = await response.json();
            
            const statusElement = document.getElementById('simulationStatus');
            statusElement.innerHTML = `
                <p><strong>Status:</strong> ${data.plc_status || 'Not connected'}</p>
                <p><strong>Variables:</strong> ${JSON.stringify(data.variables || {})}</p>
            `;
        } catch (error) {
            document.getElementById('simulationStatus').innerHTML = `<p class="error-state">Failed to get status</p>`;
        }
    }

    async loadTaskHistory() {
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            
            const taskHistory = document.getElementById('taskHistory');
            
            if (tasks.length === 0) {
                taskHistory.innerHTML = '<p class="text-muted">No recent tasks</p>';
                return;
            }

            taskHistory.innerHTML = tasks.map(task => `
                <div class="task-item">
                    <div class="task-prompt">${task.prompt}</div>
                    <div class="task-meta">
                        ${task.status} | ${task.success ? '✅' : '❌'} | ${task.quality_score || 0}/2.0
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load task history:', error);
        }
    }

    async checkSystemStatus() {
        try {
            const response = await fetch('/api/system/info');
            const data = await response.json();
            
            document.getElementById('systemStatus').textContent = 
                data.system_status === 'healthy' ? 'System OK' : 'System Issues';
        } catch (error) {
            document.getElementById('systemStatus').textContent = 'Connection Error';
        }
    }

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem;
            background: ${type === 'success' ? 'var(--success-color)' : type === 'error' ? 'var(--danger-color)' : 'var(--primary-color)'};
            color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-lg);
            z-index: 1001;
            animation: slideInRight 0.3s ease;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AutoPLCApp();
});

// Add notification animations to CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
