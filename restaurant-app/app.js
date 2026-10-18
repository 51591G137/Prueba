const API_BASE = 'https://prueba-defz.onrender.com'; // Cambia si usas otro dominio

// ----- Utilidades -----
async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Error en la petición');
  return data;
}

// ----- Usuarios -----
async function crearUsuario() {
  const username = document.getElementById('userName').value.trim();
  const email = document.getElementById('userEmail').value.trim();
  if (!username || !email) return alert('Completa nombre y email');
  try {
    await api('/api/users', 'POST', { username, email });
    await cargarUsuarios();
    document.getElementById('userName').value = '';
    document.getElementById('userEmail').value = '';
  } catch (e) { alert(e.message); }
}

async function cargarUsuarios() {
  const select = document.getElementById('userSelect');
  const users = await api('/api/users');
  select.innerHTML = '<option value="">-- Selecciona usuario --</option>' +
    users.map(u => `<option value="${u.id}">${u.username} (${u.email})</option>`).join('');
}

// ----- Restaurantes -----
async function crearRestaurante() {
  const name = document.getElementById('restName').value.trim();
  const userId = document.getElementById('userSelect').value;
  if (!name || !userId) return alert('Selecciona un usuario y escribe un nombre');
  try {
    await api('/api/restaurants', 'POST', { name, user_id: parseInt(userId) });
    await cargarRestaurantes();
    document.getElementById('restName').value = '';
  } catch (e) { alert(e.message); }
}

async function cargarRestaurantes() {
  const userId = document.getElementById('userSelect').value;
  const select = document.getElementById('restSelect');
  if (!userId) {
    select.innerHTML = '<option value="">-- Primero selecciona un usuario --</option>';
    return;
  }
  const rests = await api(`/api/restaurants?user_id=${userId}`);
  select.innerHTML = '<option value="">-- Selecciona restaurante --</option>' +
    rests.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
}

// ----- Mesas e Items -----
async function crearMesa() {
  const restaurantId = document.getElementById('restSelect').value;
  const tableNumber = document.getElementById('tableNumber').value.trim();
  const capacity = parseInt(document.getElementById('tableCapacity').value);
  if (!restaurantId || !tableNumber || !capacity) return alert('Completa los datos de la mesa');
  try {
    await api('/api/tables', 'POST', {
      restaurant_id: parseInt(restaurantId),
      table_number: tableNumber,
      capacity
    });
    await cargarMesasEItems();
    document.getElementById('tableNumber').value = '';
    document.getElementById('tableCapacity').value = '';
  } catch (e) { alert(e.message); }
}

async function crearItem() {
  const restaurantId = document.getElementById('restSelect').value;
  const name = document.getElementById('itemName').value.trim();
  const description = document.getElementById('itemDesc').value.trim();
  const price = parseFloat(document.getElementById('itemPrice').value);
  if (!restaurantId || !name || isNaN(price)) return alert('Completa los datos del plato');
  try {
    await api('/api/items', 'POST', {
      restaurant_id: parseInt(restaurantId),
      name,
      description,
      price
    });
    await cargarMesasEItems();
    document.getElementById('itemName').value = '';
    document.getElementById('itemDesc').value = '';
    document.getElementById('itemPrice').value = '';
  } catch (e) { alert(e.message); }
}

async function cargarMesasEItems() {
  const restaurantId = document.getElementById('restSelect').value;
  if (!restaurantId) return;
  // Mesas
  const tables = await api(`/api/tables?restaurant_id=${restaurantId}`);
  document.getElementById('listaMesas').innerHTML = tables
    .map(t => `<li>Mesa ${t.table_number} (cap. ${t.capacity})</li>`).join('');
  // Items
  const items = await api(`/api/items?restaurant_id=${restaurantId}`);
  document.getElementById('listaItems').innerHTML = items
    .map(i => `<li>${i.name} - $${i.price.toFixed(2)} ${i.description ? `(${i.description})` : ''}</li>`).join('');
}

// ----- Reservas del día -----
async function cargarReservas() {
  const restaurantId = document.getElementById('restSelect').value;
  if (!restaurantId) return alert('Selecciona un restaurante');
  const hoy = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  const reservas = await api(`/api/reservations?restaurant_id=${restaurantId}&date=${hoy}`);
  document.getElementById('listaReservas').innerHTML = reservas.length
    ? reservas.map(r => `<li>Mesa ${r.table_number} - ${r.reservation_datetime} - Cliente: ${r.customer_name}</li>`).join('')
    : '<li>No hay reservas para hoy</li>';
}

// ----- Inicialización -----
cargarUsuarios();