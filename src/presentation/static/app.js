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
    } else if (tab === 'properties') {
        tabTitle.textContent = 'Imóveis Cadastrados';
        tabSubtitle.textContent = 'Importe imóveis do site Exata Serviços ou cadastre-os manualmente e filtre-os';
        loadProperties();
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

    // --- Eventos do Dashboard de Imóveis ---
    document.getElementById('btn-refresh-properties').addEventListener('click', loadProperties);
    document.getElementById('btn-clear-prop-filters').addEventListener('click', clearPropertyFilters);
    document.getElementById('btn-apply-prop-filters').addEventListener('click', loadProperties);
    document.getElementById('property-scraper-form').addEventListener('submit', runPropertyScraper);
    document.getElementById('btn-new-property').addEventListener('click', openPropertyAddModal);
    
    document.getElementById('btn-close-property-modal').addEventListener('click', closePropertyModal);
    document.getElementById('btn-close-property-form').addEventListener('click', closePropertyModal);
    document.getElementById('property-modal-form').addEventListener('submit', savePropertyForm);
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

// --- ABA 4: IMÓVEIS (LÓGICA) ---
async function loadProperties() {
    const tableBody = document.getElementById('properties-table-body');
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center">Buscando imóveis...</td></tr>`;

    const intent = document.getElementById('prop-filter-intent').value;
    const type = document.getElementById('prop-filter-type').value;
    const bedrooms = document.getElementById('prop-filter-bedrooms').value;
    const bathrooms = document.getElementById('prop-filter-bathrooms').value;
    const parking = document.getElementById('prop-filter-parking').value;
    const neighborhood = document.getElementById('prop-filter-neighborhood').value.trim();
    const minPrice = document.getElementById('prop-filter-min-price').value;
    const maxPrice = document.getElementById('prop-filter-max-price').value;

    let url = `${API_BASE}/properties?`;
    if (intent) url += `&intent=${encodeURIComponent(intent)}`;
    if (type) url += `&property_type=${encodeURIComponent(type)}`;
    if (bedrooms) url += `&bedrooms=${bedrooms}`;
    if (bathrooms) url += `&bathrooms=${bathrooms}`;
    if (parking) url += `&parking_spaces=${parking}`;
    if (neighborhood) url += `&neighborhood=${encodeURIComponent(neighborhood)}`;
    if (minPrice) url += `&min_price=${minPrice}`;
    if (maxPrice) url += `&max_price=${maxPrice}`;

    try {
        const response = await fetchAuth(url);
        if (!response.ok) throw new Error('Falha ao obter imóveis');
        const properties = await response.json();

        if (properties.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Nenhum imóvel cadastrado no banco de dados. Use o scraper acima para importar!</td></tr>`;
            return;
        }

        tableBody.innerHTML = properties.map(p => {
            const priceFmt = p.value ? 'R$ ' + p.value.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : 'R$ 0,00';
            const feesFmt = p.fees ? 'R$ ' + p.fees.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '-';
            const intentBadge = p.intent && p.intent.toLowerCase().includes('venda') 
                ? '<span class="badge badge-out">Venda</span>' 
                : '<span class="badge badge-in">Aluguel</span>';
            
            const bedroomsHtml = p.bedrooms !== null && p.bedrooms !== undefined ? `<span class="prop-badge">🛏️ ${p.bedrooms}</span>` : '';
            const bathroomsHtml = p.bathrooms !== null && p.bathrooms !== undefined ? `<span class="prop-badge">🚿 ${p.bathrooms}</span>` : '';
            const parkingHtml = p.parking_spaces !== null && p.parking_spaces !== undefined ? `<span class="prop-badge">🚗 ${p.parking_spaces}</span>` : '';
            
            const descTrunc = p.description ? (p.description.length > 80 ? p.description.substring(0, 80) + '...' : p.description) : '-';

            const photoUrl = p.photos && p.photos.length > 0 ? p.photos[0] : '';
            const imgHtml = photoUrl ? `<img class="prop-image-thumb" src="${escapeHtml(photoUrl)}" alt="Foto">` : '<div class="prop-image-thumb text-center" style="display:flex;align-items:center;justify-content:center;font-size:1.5rem;">🏡</div>';

            return `
                <tr>
                    <td>
                        <div style="display:flex;align-items:center;gap:12px;">
                            ${imgHtml}
                            <div>
                                <span class="text-bold">${escapeHtml(p.ref || 'S/Ref')}</span><br>
                                <span class="text-muted" style="font-size:0.75rem;">ID: ${escapeHtml(p.id)}</span>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="text-bold">${escapeHtml(p.property_type)}</span><br>
                        ${intentBadge}
                    </td>
                    <td>
                        <span>${escapeHtml(p.address)}</span><br>
                        <span class="text-muted" style="font-size:0.8rem;">📍 Bairro: ${escapeHtml(p.neighborhood)}</span>
                    </td>
                    <td>
                        <span class="text-bold" style="color:var(--primary-color);">${priceFmt}</span><br>
                        <span class="text-muted" style="font-size:0.8rem;">Taxas: ${feesFmt}</span>
                    </td>
                    <td>
                        <div class="prop-details-badges">
                            ${bedroomsHtml}
                            ${bathroomsHtml}
                            ${parkingHtml}
                        </div>
                        <div class="text-muted" style="font-size:0.75rem;margin-top:6px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                            ${escapeHtml(descTrunc.replace(/\n/g, ' '))}
                        </div>
                    </td>
                    <td>
                        <div class="prop-actions">
                            <button class="btn-action-icon copy" title="Copiar Detalhes (WhatsApp)" onclick='copyPropertyDetails(${rawJsonAttr(p)})'>📋</button>
                            <button class="btn-action-icon edit" title="Editar Imóvel" onclick='openPropertyEditModal(${rawJsonAttr(p)})'>✏️</button>
                            <button class="btn-action-icon delete" title="Excluir Imóvel" onclick="deleteProperty('${p.id}')">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Erro: ${err.message}</td></tr>`;
    }
}

// Limpa filtros
function clearPropertyFilters() {
    document.getElementById('prop-filter-intent').value = '';
    document.getElementById('prop-filter-type').value = '';
    document.getElementById('prop-filter-bedrooms').value = '';
    document.getElementById('prop-filter-bathrooms').value = '';
    document.getElementById('prop-filter-parking').value = '';
    document.getElementById('prop-filter-neighborhood').value = '';
    document.getElementById('prop-filter-min-price').value = '';
    document.getElementById('prop-filter-max-price').value = '';
    loadProperties();
}

// Executa scraper
async function runPropertyScraper(e) {
    e.preventDefault();
    const refInput = document.getElementById('scraper-ref');
    const ref = refInput.value.trim();
    const statusBox = document.getElementById('scraper-status');

    if (!ref) return;

    statusBox.className = 'scraper-status-box loading';
    statusBox.innerHTML = `<span>⏳ Procurando e raspando referência ${ref}...</span>`;

    try {
        const response = await fetchAuth(`${API_BASE}/properties/scrape`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ref: ref })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Imóvel não encontrado ou falha no scraping');
        }

        const data = await response.json();
        statusBox.className = 'scraper-status-box success';
        statusBox.innerHTML = `<span>✅ Imóvel ${ref} importado com sucesso no banco!</span>`;
        refInput.value = '';

        loadProperties();
        
        if (data.property) {
            setTimeout(() => {
                openPropertyEditModal(data.property);
            }, 800);
        }
    } catch (err) {
        statusBox.className = 'scraper-status-box error';
        statusBox.innerHTML = `<span>❌ Erro: ${err.message}</span>`;
    }
}

const propertyModal = document.getElementById('property-modal');

window.openPropertyEditModal = function(p) {
    document.getElementById('property-modal-title').textContent = 'Editar Detalhes do Imóvel';
    document.getElementById('property-modal-id').value = p.id;
    
    document.getElementById('property-modal-ref').value = p.ref || '';
    document.getElementById('property-modal-ref').disabled = false;
    document.getElementById('property-modal-type').value = p.property_type || 'Casa';
    document.getElementById('property-modal-intent').value = p.intent || 'Locação';
    document.getElementById('property-modal-value').value = p.value || 0;
    document.getElementById('property-modal-fees').value = p.fees || 0;
    document.getElementById('property-modal-url').value = p.url || '';
    document.getElementById('property-modal-address').value = p.address || '';
    document.getElementById('property-modal-neighborhood').value = p.neighborhood || '';
    
    document.getElementById('property-modal-bedrooms').value = p.bedrooms !== null && p.bedrooms !== undefined ? p.bedrooms : '';
    document.getElementById('property-modal-bathrooms').value = p.bathrooms !== null && p.bathrooms !== undefined ? p.bathrooms : '';
    document.getElementById('property-modal-parking').value = p.parking_spaces !== null && p.parking_spaces !== undefined ? p.parking_spaces : '';
    document.getElementById('property-modal-description').value = p.description || '';
    document.getElementById('property-modal-photos').value = p.photos ? p.photos.join('\n') : '';

    propertyModal.classList.add('active');
};

window.openPropertyAddModal = function() {
    document.getElementById('property-modal-title').textContent = 'Cadastrar Novo Imóvel';
    document.getElementById('property-modal-id').value = 'new_' + Math.random().toString(36).substr(2, 9);
    
    document.getElementById('property-modal-ref').value = '';
    document.getElementById('property-modal-ref').disabled = false;
    document.getElementById('property-modal-type').value = 'Casa';
    document.getElementById('property-modal-intent').value = 'Locação';
    document.getElementById('property-modal-value').value = '';
    document.getElementById('property-modal-fees').value = '';
    document.getElementById('property-modal-url').value = '';
    document.getElementById('property-modal-address').value = '';
    document.getElementById('property-modal-neighborhood').value = '';
    
    document.getElementById('property-modal-bedrooms').value = '';
    document.getElementById('property-modal-bathrooms').value = '';
    document.getElementById('property-modal-parking').value = '';
    document.getElementById('property-modal-description').value = '';
    document.getElementById('property-modal-photos').value = '';

    propertyModal.classList.add('active');
};

function closePropertyModal() {
    propertyModal.classList.remove('active');
}

async function savePropertyForm(e) {
    e.preventDefault();

    const id = document.getElementById('property-modal-id').value;
    const ref = document.getElementById('property-modal-ref').value.trim();
    const type = document.getElementById('property-modal-type').value;
    const intent = document.getElementById('property-modal-intent').value;
    const value = parseFloat(document.getElementById('property-modal-value').value) || 0;
    const fees = parseFloat(document.getElementById('property-modal-fees').value) || 0;
    const url = document.getElementById('property-modal-url').value.trim();
    const address = document.getElementById('property-modal-address').value.trim();
    const neighborhood = document.getElementById('property-modal-neighborhood').value.trim();
    
    const bedrooms = document.getElementById('property-modal-bedrooms').value;
    const bathrooms = document.getElementById('property-modal-bathrooms').value;
    const parking = document.getElementById('property-modal-parking').value;
    
    const description = document.getElementById('property-modal-description').value;
    const photosText = document.getElementById('property-modal-photos').value.trim();
    const photos = photosText ? photosText.split('\n').map(p => p.trim()).filter(Boolean) : [];

    const finalId = id.startsWith('new_') ? (ref ? ref : Math.random().toString(36).substr(2, 9)) : id;

    const data = {
        id: finalId,
        ref: ref,
        property_type: type,
        intent: intent,
        value: value,
        fees: fees,
        url: url,
        address: address,
        neighborhood: neighborhood,
        bedrooms: bedrooms !== '' ? parseInt(bedrooms, 10) : null,
        bathrooms: bathrooms !== '' ? parseInt(bathrooms, 10) : null,
        parking_spaces: parking !== '' ? parseInt(parking, 10) : null,
        description: description,
        photos: photos
    };

    try {
        const response = await fetchAuth(`${API_BASE}/properties/${encodeURIComponent(finalId)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) throw new Error('Falha ao salvar imóvel no banco');

        closePropertyModal();
        loadProperties();
        alert('Imóvel salvo com sucesso!');
    } catch (err) {
        alert(`Erro: ${err.message}`);
    }
}

window.deleteProperty = async function(id) {
    if (!confirm('Deseja realmente excluir este imóvel do banco de dados?')) return;

    try {
        const response = await fetchAuth(`${API_BASE}/properties/${encodeURIComponent(id)}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Falha ao excluir imóvel');
        loadProperties();
    } catch (err) {
        alert(`Erro: ${err.message}`);
    }
};

window.copyPropertyDetails = function(p) {
    const valueFmt = p.value ? p.value.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '0,00';
    const feesFmt = p.fees ? p.fees.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '';

    let street = p.address;
    let number = '';
    let complement = '';

    const parts = p.address.split(',');
    if (parts.length > 1) {
        street = parts[0].trim();
        const secondPart = parts[1].split('-');
        number = secondPart[0].trim();
        if (secondPart.length > 1) {
            complement = secondPart[1].trim();
        }
    }

    const template = `Detalhe imóvel
 
Código: ${p.ref || 'S/Ref'}
Endereço: ${street}
Número: ${number}
Bairro: ${p.neighborhood || ''}
Complemento: ${complement || p.property_type || ''}
Taxas R$: ${feesFmt}
Valor R$: ${valueFmt}
 
Descrição:
${p.description || ''}`;

    navigator.clipboard.writeText(template).then(() => {
        const toast = document.getElementById('copy-toast');
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2000);
    }).catch(err => {
        console.error('Falha ao copiar detalhes:', err);
    });
};
