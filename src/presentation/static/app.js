// ==========================================
// CONFIGURAÇÕES GERAIS E ESTADO DO FRONTEND
// ==========================================
const API_BASE = '/api/admin';
let currentToken = localStorage.getItem('exatabot_token') || null;

// Referências aos Containers Principais
const loginContainer = document.getElementById('login-container');
const appContainer = document.getElementById('app-container');

// ==========================================
// INICIALIZAÇÃO DA PÁGINA
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupNavigation();
    setupForms();
});

// ==========================================
// CONTROLE DE AUTENTICAÇÃO
// ==========================================
function checkAuth() {
    if (currentToken) {
        // Exibe Dashboard, oculta Login
        loginContainer.classList.remove('active');
        appContainer.classList.add('active');
        loadTabContent('logs'); // Tab padrão inicial
    } else {
        // Exibe Login, oculta Dashboard
        appContainer.classList.remove('active');
        loginContainer.classList.add('active');
    }
}

// Formulário de Login
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errorText = document.getElementById('login-error');
    errorText.textContent = '';

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Usuário ou senha incorretos');
        }

        const data = await response.json();
        currentToken = data.access_token;
        localStorage.setItem('exatabot_token', currentToken);
        checkAuth();
    } catch (err) {
        errorText.textContent = err.message;
    }
});

// Botão de Logout
document.getElementById('logout-btn').addEventListener('click', () => {
    currentToken = null;
    localStorage.removeItem('exatabot_token');
    checkAuth();
});

// Wrapper para requisições Fetch Autenticadas
async function fetchAuth(url, options = {}) {
    if (!options.headers) {
        options.headers = {};
    }
    options.headers['Authorization'] = `Bearer ${currentToken}`;

    const response = await fetch(url, options);
    if (response.status === 401) {
        // Se o token expirou ou é inválido, desloga
        currentToken = null;
        localStorage.removeItem('exatabot_token');
        checkAuth();
        throw new Error('Sessão expirada. Faça login novamente.');
    }
    return response;
}

// ==========================================
// NAVEGAÇÃO E CONTROLE DE ABAS (TABS)
// ==========================================
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            const tab = link.getAttribute('data-tab');
            loadTabContent(tab);
        });
    });
}

function loadTabContent(tab) {
    // Esconde todos os conteúdos
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    // Exibe o conteúdo selecionado
    const targetContent = document.getElementById(`tab-content-${tab}`);
    if (targetContent) {
        targetContent.classList.add('active');
    }

    // Configura os textos do Header
    const tabTitle = document.getElementById('tab-title');
    const tabSubtitle = document.getElementById('tab-subtitle');

    if (tab === 'logs') {
        tabTitle.textContent = 'Conversas & Logs';
        tabSubtitle.textContent = 'Monitore as conversas enviadas e recebidas do WhatsApp em tempo real';
        loadLogs();
    } else if (tab === 'brokers') {
        tabTitle.textContent = 'Gestão de Corretores';
        tabSubtitle.textContent = 'Cadastre e gerencie as imobiliárias / corretores e suas instâncias correspondentes';
        loadBrokers();
    } else if (tab === 'subscriptions') {
        tabTitle.textContent = 'Alertas Ativos';
        tabSubtitle.textContent = 'Gerencie as assinaturas de alertas de novos imóveis criadas pelos usuários';
        loadSubscriptions();
    }
}

// ==========================================
// LÓGICA DE CADA ABA DO DASHBOARD
// ==========================================

// --- ABA 1: LOGS DE AUDITORIA ---
async function loadLogs() {
    const tableBody = document.getElementById('logs-table-body');
    const phone = document.getElementById('filter-phone').value.trim();
    const limit = document.getElementById('filter-limit').value;

    tableBody.innerHTML = `<tr><td colspan="6" class="text-center">Buscando registros...</td></tr>`;

    let url = `${API_BASE}/logs?limit=${limit}`;
    if (phone) {
        url += `&phone=${encodeURIComponent(phone)}`;
    }

    try {
        const response = await fetchAuth(url);
        if (!response.ok) throw new Error('Falha ao obter logs');
        const logs = await response.json();

        if (logs.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Nenhum registro encontrado.</td></tr>`;
            return;
        }

        tableBody.innerHTML = logs.map(log => {
            const dateStr = new Date(log.created_at).toLocaleString('pt-BR');
            const directionBadge = log.direction === 'in' 
                ? '<span class="badge badge-in">Recebida</span>' 
                : '<span class="badge badge-out">Enviada</span>';
            
            return `
                <tr>
                    <td class="text-bold">${dateStr}</td>
                    <td>${log.phone}</td>
                    <td>${directionBadge}</td>
                    <td>${log.step}</td>
                    <td>${log.intent || '-'}</td>
                    <td>${escapeHtml(log.text)}</td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Erro: ${err.message}</td></tr>`;
    }
}

// --- ABA 2: GESTÃO DE CORRETORES ---
async function loadBrokers() {
    const listContainer = document.getElementById('brokers-list-container');
    listContainer.innerHTML = `<p class="text-center">Carregando corretores...</p>`;

    try {
        const response = await fetchAuth(`${API_BASE}/brokers`);
        if (!response.ok) throw new Error('Falha ao obter corretores');
        const brokers = await response.json();

        if (brokers.length === 0) {
            listContainer.innerHTML = `<p class="text-center text-muted">Nenhum corretor cadastrado ainda.</p>`;
            return;
        }

        listContainer.innerHTML = brokers.map(b => `
            <div class="broker-card ${b.is_active ? '' : 'inactive'}">
                <div class="broker-card-info">
                    <h4>${escapeHtml(b.broker_name)}</h4>
                    <p>
                        <strong>Instância:</strong> ${escapeHtml(b.instance_id)}<br>
                        <strong>Telefone:</strong> ${escapeHtml(b.phone_number)}<br>
                        <strong>Bot (Atendente):</strong> ${escapeHtml(b.bot_name)}<br>
                        <strong>URL Site:</strong> <a href="${escapeHtml(b.site_base_url)}" target="_blank">${escapeHtml(b.site_base_url)}</a>
                    </p>
                </div>
                <div class="broker-card-actions">
                    <button class="btn btn-secondary btn-sm" onclick="editBroker(${rawJsonAttr(b)})">Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteBroker('${b.instance_id}')">Deletar</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        listContainer.innerHTML = `<p class="text-center text-danger">Erro: ${err.message}</p>`;
    }
}

// Preenche o formulário CRUD para edição
window.editBroker = function(broker) {
    document.getElementById('form-broker-title').textContent = 'Editar Corretor';
    
    const instIdInput = document.getElementById('broker-instance-id');
    instIdInput.value = broker.instance_id;
    // Não permite alterar o ID da instância (chave primária) na edição para evitar conflitos
    instIdInput.disabled = true;

    document.getElementById('broker-name').value = broker.broker_name;
    document.getElementById('broker-phone').value = broker.phone_number;
    document.getElementById('broker-site-url').value = broker.site_base_url;
    document.getElementById('broker-bot-name').value = broker.bot_name;
    document.getElementById('broker-active').checked = broker.is_active;
};

// Limpa o formulário CRUD
function clearBrokerForm() {
    document.getElementById('form-broker-title').textContent = 'Novo Corretor / Imobiliária';
    
    const instIdInput = document.getElementById('broker-instance-id');
    instIdInput.value = '';
    instIdInput.disabled = false;

    document.getElementById('broker-name').value = '';
    document.getElementById('broker-phone').value = '';
    document.getElementById('broker-site-url').value = '';
    document.getElementById('broker-bot-name').value = 'Ana';
    document.getElementById('broker-active').checked = true;
}

// Exclui um corretor
window.deleteBroker = async function(instanceId) {
    if (!confirm(`Tem certeza que deseja excluir o corretor da instância "${instanceId}"? Esta ação é irreversível.`)) {
        return;
    }

    try {
        const response = await fetchAuth(`${API_BASE}/brokers/${encodeURIComponent(instanceId)}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Falha ao excluir corretor');
        loadBrokers();
        clearBrokerForm();
    } catch (err) {
        alert(`Erro: ${err.message}`);
    }
};

// --- ABA 3: ALERTAS ATIVOS (ASSINATURAS) ---
async function loadSubscriptions() {
    const tableBody = document.getElementById('subs-table-body');
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center">Buscando assinaturas...</td></tr>`;

    try {
        const response = await fetchAuth(`${API_BASE}/subscriptions`);
        if (!response.ok) throw new Error('Falha ao obter assinaturas');
        const subs = await response.json();

        if (subs.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Nenhum alerta ativo encontrado.</td></tr>`;
            return;
        }

        tableBody.innerHTML = subs.map(sub => `
            <tr>
                <td class="text-bold">${sub.phone}</td>
                <td>${sub.intent}</td>
                <td>${sub.property_type}</td>
                <td>${sub.neighborhood}</td>
                <td>${sub.max_value ? 'R$ ' + sub.max_value.toLocaleString('pt-BR') : '-'}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="cancelSubscription('${sub.phone}')">Remover</button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Erro: ${err.message}</td></tr>`;
    }
}

// Cancela a assinatura de um cliente
window.cancelSubscription = async function(phone) {
    if (!confirm(`Tem certeza que deseja cancelar os alertas para o telefone ${phone}?`)) {
        return;
    }

    try {
        const response = await fetchAuth(`${API_BASE}/subscriptions/${encodeURIComponent(phone)}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Falha ao remover assinatura');
        loadSubscriptions();
    } catch (err) {
        alert(`Erro: ${err.message}`);
    }
};

// ==========================================
// CONFIGURAÇÃO DOS EVENTOS DOS FORMULÁRIOS
// ==========================================
function setupForms() {
    // Recarregar/Filtrar Logs
    document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);
    
    // Atualizar Corretores
    document.getElementById('btn-refresh-brokers').addEventListener('click', loadBrokers);
    
    // Atualizar Assinaturas
    document.getElementById('btn-refresh-subs').addEventListener('click', loadSubscriptions);

    // Botão Limpar Formulário do Corretor
    document.getElementById('btn-clear-broker-form').addEventListener('click', clearBrokerForm);

    // Envio do formulário de Corretor (Criar/Atualizar)
    document.getElementById('broker-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = {
            instance_id: document.getElementById('broker-instance-id').value.trim(),
            broker_name: document.getElementById('broker-name').value.trim(),
            phone_number: document.getElementById('broker-phone').value.trim(),
            site_base_url: document.getElementById('broker-site-url').value.trim(),
            bot_name: document.getElementById('broker-bot-name').value.trim(),
            is_active: document.getElementById('broker-active').checked
        };

        try {
            const response = await fetchAuth(`${API_BASE}/brokers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Falha ao salvar corretor');
            }

            loadBrokers();
            clearBrokerForm();
            alert('Perfil de corretor salvo com sucesso!');
        } catch (err) {
            alert(`Erro: ${err.message}`);
        }
    });
}

// ==========================================
// FUNÇÕES AUXILIARES UTILITÁRIAS
// ==========================================
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#039;');
}

function rawJsonAttr(obj) {
    return escapeHtml(JSON.stringify(obj));
}
