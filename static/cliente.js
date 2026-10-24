'use strict';
/* App de clientes: cliente -> restaurantes -> mesas (con reserva) y menú.
   Añade: "Mis reservas" con edición y borrado.
   Rutas: #/ · #/c/3 · #/c/3/reservas · #/c/3/r/7/mesas|menu */

const TABS = [
  ['mesas', 'Mesas'],
  ['menu', 'Menú'],
];

startRouter((parts, isStale) => {
  const [a, customerId, b, restaurantId, tab] = parts;
  if (a === 'c' && customerId && b === 'reservas') return viewMyReservations(customerId, isStale);
  if (a === 'c' && customerId && b === 'r' && restaurantId) return viewRestaurant(customerId, restaurantId, tab, isStale);
  if (a === 'c' && customerId) return viewRestaurants(customerId, isStale);
  return viewCustomers(isStale);
});

/* ---------- Clientes ---------- */

async function viewCustomers(isStale) {
  const title = 'Reserva tu mesa';
  setScreen(title, null, loading());
  const customers = await api('/api/customers');
  if (isStale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        const customer = await api('/api/customers', { method: 'POST', body: data });
        toast('Cliente creado');
        location.hash = `#/c/${customer.id}`;
      }),
    },
    h('h2', null, 'Nuevo cliente'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 80, autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Crear cliente'),
  );

  const rows = customers.map((customer) =>
    h('li', null, h('a', { class: 'row', href: `#/c/${customer.id}` }, h('strong', null, customer.name))),
  );
  setScreen(
    title,
    null,
    h('h2', null, 'Elige un cliente'),
    h('ul', { class: 'list' }, rows.length ? rows : empty('Todavía no hay clientes. Crea el primero.')),
    form,
  );
}

/* ---------- Todos los restaurantes ---------- */

async function viewRestaurants(customerId, isStale) {
  setScreen('Cargando…', '#/', loading());
  const [customer, restaurants] = await Promise.all([
    api(`/api/customers/${customerId}`),
    api('/api/restaurants'),
  ]);
  if (isStale()) return;

  const rows = restaurants.map((restaurant) =>
    h('li', null, h(
      'a',
      { class: 'row', href: `#/c/${customerId}/r/${restaurant.id}/mesas` },
      h('div', { class: 'grow' },
        h('strong', null, restaurant.name),
        restaurant.address && h('div', { class: 'muted small' }, restaurant.address)),
    )),
  );

  setScreen(
    `Hola, ${customer.name}`,
    '#/',
    h('a', { class: 'btn ghost', href: `#/c/${customerId}/reservas` }, 'Mis reservas'),
    h('h2', null, 'Restaurantes'),
    h('ul', { class: 'list' }, rows.length ? rows : empty('Todavía no hay restaurantes. Vuelve más tarde.')),
  );
}

/* ---------- Mis reservas ---------- */

async function viewMyReservations(customerId, isStale) {
  setScreen('Cargando…', `#/c/${customerId}`, loading());
  const reservations = await api(`/api/customers/${customerId}/reservations`);
  if (isStale()) return;

  const list = h('ul', { class: 'list ledger' }, ...(reservations.length
    ? reservations.map((r) => h('li', { class: 'ledger-row' },
        h('div', { class: 'time' }, `${formatDate(r.date)} ${r.time}`),
        h('div', { class: 'what' },
          h('strong', null, r.restaurant),
          h('div', { class: 'muted' }, `Mesa ${r.table}`),
          h('div', { class: 'actions' },
            h('button', {
              class: 'btn small ghost', type: 'button',
              onclick: async () => {
                const newDate = prompt('Nueva fecha (AAAA-MM-DD):', r.date);
                if (newDate === null) return;
                const newTime = prompt('Nueva hora (HH:MM):', r.time);
                if (newTime === null) return;
                try {
                  await api(`/api/reservations/${r.id}`, {
                    method: 'PATCH', body: { date: newDate, time: newTime },
                  });
                  toast('Reserva actualizada');
                  await viewMyReservations(customerId, isStale);
                } catch (err) { toast(err.message, true); }
              },
            }, 'Editar'),
            h('button', {
              class: 'btn small danger', type: 'button',
              onclick: async () => {
                if (!confirm('¿Cancelar esta reserva?')) return;
                try {
                  await api(`/api/reservations/${r.id}`, { method: 'DELETE' });
                  toast('Reserva cancelada');
                  await viewMyReservations(customerId, isStale);
                } catch (err) { toast(err.message, true); }
              },
            }, 'Cancelar'),
          ),
        ),
      )),
    : [empty('Todavía no has hecho reservas.')],
  ));

  setScreen(
    'Mis reservas',
    `#/c/${customerId}`,
    list,
  );
}

/* ---------- Un restaurante: mesas con reserva y menú ---------- */

async function viewRestaurant(customerId, restaurantId, tab, isStale) {
  const back = `#/c/${customerId}`;
  setScreen('Cargando…', back, loading());
  const restaurant = await api(`/api/restaurants/${restaurantId}`);
  if (isStale()) return;

  const tabs = { mesas: tabTables, menu: tabMenu };
  if (!tabs[tab]) tab = 'mesas';
  const box = h('div');
  setScreen(
    restaurant.name,
    back,
    restaurant.address && h('p', { class: 'muted address' }, restaurant.address),
    tabBar(`#/c/${customerId}/r/${restaurantId}`, TABS, tab),
    box,
  );
  await tabs[tab](customerId, restaurantId, box, isStale);
}

async function tabTables(customerId, restaurantId, box, isStale) {
  const date = h('input', { name: 'date', type: 'date', value: todayStr(), min: todayStr(), required: true });
  const time = timeSelect('21:00');
  const list = h('ul', { class: 'list' });
  let latest = 0;
  const params = () => new URLSearchParams({ date: date.value, time: time.value });

  async function refresh() {
    if (!date.value) {
      latest++;
      list.removeAttribute('aria-busy');
      list.replaceChildren(empty('Elige una fecha para ver las mesas libres.'));
      return;
    }
    const request = ++latest;
    list.setAttribute('aria-busy', 'true');
    let tables;
    try {
      tables = await api(`/api/restaurants/${restaurantId}/tables?${params()}`);
    } finally {
      if (request === latest) list.removeAttribute('aria-busy');
    }
    if (request !== latest || isStale()) return;
    const rows = tables.map((table) =>
      h('li', null, h(
        'div',
        { class: table.reserved ? 'row taken' : 'row' },
        h('div', { class: 'grow' },
          h('strong', null, table.name),
          h('div', { class: 'muted small' }, people(table.capacity))),
        table.reserved
          ? h('span', { class: 'status' }, 'Reservada')
          : h('button', {
              class: 'btn small', type: 'button',
              onclick: (event) => reserve(table, event.currentTarget),
            }, 'Reservar'),
      )),
    );
    list.replaceChildren(...(rows.length ? rows : [empty('Este restaurante aún no ha añadido mesas.')]));
  }

  async function reserve(table, button) {
    button.disabled = true;
    try {
      await api('/api/reservations', {
        method: 'POST',
        body: { customer_id: customerId, table_id: table.id, date: date.value, time: time.value },
      });
      toast(`Reserva confirmada: ${table.name}, ${formatDate(date.value)} a las ${time.value}.`);
    } catch (err) {
      toast(err.message, true);
    }
    await refresh().catch((err) => toast(err.message, true));
  }

  const reload = () => refresh().catch((err) => toast(err.message, true));
  date.addEventListener('change', reload);
  time.addEventListener('change', reload);

  box.append(h('div', { class: 'panel' }, h('div', { class: 'pair' }, field('Fecha', date), field('Hora', time))), list);
  await refresh();
}

async function tabMenu(customerId, restaurantId, box, isStale) {
  const items = await api(`/api/restaurants/${restaurantId}/menu`);
  if (isStale()) return;
  box.append(menuList(items, 'Este restaurante aún no ha publicado su menú.'));
}