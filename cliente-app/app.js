const API_BASE = 'https://prueba-defz.onrender.com';

async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Error en la petición');
  return data;
}

// ----- Clientes -----
async function crearCliente() {
  const name = document.getElementById('custName').value.trim();
  const email = document.getElementById('custEmail').value.trim();
  if (!name || !email) return alert('Completa nombre y email');
  try {
    await api('/api/customers', 'POST', { name, email });
    await cargarClientes();
    document.getElementById('custName').value = '';
    document.getElementById('custEmail').value = '';
  } catch (e) { alert(e.message); }
}

async function cargarClientes() {
  const select = document.getElementById('custSelect');
  const clientes = await api('/api/customers');
  select.innerHTML = '<option value="">-- Selecciona cliente --</option>' +
    clientes.map(c => `<option value="${c.id}">${c.name} (${c.email})</option>`).join('');
}

// ----- Restaurantes -----
async function cargarRestaurantes() {
  const select = document.getElementById('restSelect');
  const rests = await api('/api/restaurants');
  select.innerHTML = '<option value="">-- Selecciona restaurante --</option>' +
    rests.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
}

// ----- Mesas y menú del restaurante seleccionado -----
async function cargarMesasEItems() {
  const restId = document.getElementById('restSelect').value;
  if (!restId) return;
  // Mesas
  const mesas = await api(`/api/tables?restaurant_id=${restId}`);
  document.getElementById('mesasContainer').innerHTML = '<h3>Mesas</h3>' +
    (mesas.length ? '<ul>' + mesas.map(m => `<li>Mesa ${m.table_number} (cap. ${m.capacity})</li>`).join('') + '</ul>' : '<p>No hay mesas</p>');
  // Items
  const items = await api(`/api/items?restaurant_id=${restId}`);
  document.getElementById('itemsContainer').innerHTML = '<h3>Menú</h3>' +
    (items.length ? '<ul>' + items.map(i => `<li>${i.name} - $${i.price.toFixed(2)} ${i.description ? `(${i.description})` : ''}</li>`).join('') + '</ul>' : '<p>No hay platos</p>');
  // Selector de mesas para reservar
  const selectMesa = document.getElementById('reservaMesaSelect');
  selectMesa.innerHTML = mesas.map(m => `<option value="${m.id}">Mesa ${m.table_number}</option>`).join('');
}

// ----- Reservar -----
async function reservar() {
  const customerId = document.getElementById('custSelect').value;
  const tableId = document.getElementById('reservaMesaSelect').value;
  const fecha = document.getElementById('reservaFecha').value; // "YYYY-MM-DDTHH:MM"
  if (!customerId || !tableId || !fecha) return alert('Selecciona cliente, mesa y fecha/hora');
  try {
    await api('/api/reservations', 'POST', {
      table_id: parseInt(tableId),
      customer_id: parseInt(customerId),
      reservation_datetime: fecha
    });
    alert('✅ Reserva creada correctamente');
  } catch (e) { alert(e.message); }
}

// ----- Inicialización -----
cargarClientes();