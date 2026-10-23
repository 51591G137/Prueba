'use strict';
/* App de restaurantes: usuario -> restaurantes -> mesas, menú y reservas.
   Rutas: #/ · #/u/3 · #/u/3/r/7/mesas|menu|reservas */

const TABS = [
  ['mesas', 'Mesas'],
  ['menu', 'Menú'],
  ['reservas', 'Reservas'],
];

startRouter((parts, isStale) => {
  const [a, userId, b, restaurantId, tab] = parts;
  if (a === 'u' && userId && b === 'r' && restaurantId) return viewRestaurant(userId, restaurantId, tab, isStale);
  if (a === 'u' && userId) return viewUser(userId, isStale);
  return viewUsers(isStale);
});

/* ---------- Usuarios ---------- */

async function viewUsers(isStale) {
  const title = 'Gestión del restaurante';
  setScreen(title, null, loading());
  const users = await api('/api/users');
  if (isStale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        const user = await api('/api/users', { method: 'POST', body: data });
        toast('Usuario creado');
        location.hash = `#/u/${user.id}`;
      }),
    },
    h('h2', null, 'Nuevo usuario'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 80, autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Crear usuario'),
  );

  const rows = users.map((user) =>
    h('li', null, h('a', { class: 'row', href: `#/u/${user.id}` }, h('strong', null, user.name))),
  );
  setScreen(
    title,
    null,
    h('h2', null, 'Elige un usuario'),
    h('ul', { class: 'list' }, rows.length ? rows : empty('Todavía no hay usuarios. Crea el primero.')),
    form,
  );
}

/* ---------- Restaurantes de un usuario ---------- */

async function viewUser(userId, isStale) {
  setScreen('Cargando…', '#/', loading());
  const user = await api(`/api/users/${userId}`);
  if (isStale()) return;

  const list = h('ul', { class: 'list' });

  async function refresh() {
    const restaurants = await api(`/api/users/${userId}/restaurants`);
    if (isStale()) return;
    const rows = restaurants.map((restaurant) =>
      h(
        'li',
        null,
        h(
          'a',
          { class: 'row', href: `#/u/${userId}/r/${restaurant.id}/mesas` },
          h('div', { class: 'grow' }, h('strong', null, restaurant.name), restaurant.address && h('div', { class: 'muted small' }, restaurant.address)),
        ),
      ),
    );
    list.replaceChildren(...(rows.length ? rows : [empty('Todavía no tienes restaurantes. Crea el primero abajo.')]));
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api(`/api/users/${userId}/restaurants`, { method: 'POST', body: data });
        f.reset();
        toast('Restaurante creado');
        await refresh();
      }),
    },
    h('h2', null, 'Nuevo restaurante'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 120, autocomplete: 'off' })),
    field('Dirección (opcional)', h('input', { name: 'address', type: 'text', maxlength: 200, autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Crear restaurante'),
  );

  setScreen(`Hola, ${user.name}`, '#/', h('h2', null, 'Tus restaurantes'), list, form);
  await refresh();
}

/* ---------- Un restaurante: mesas, menú y reservas ---------- */

async function viewRestaurant(userId, restaurantId, tab, isStale) {
  const back = `#/u/${userId}`;
  setScreen('Cargando…', back, loading());
  const restaurant = await api(`/api/restaurants/${restaurantId}`);
  if (isStale()) return;

  const tabs = { mesas: tabTables, menu: tabMenu, reservas: tabReservations };
  if (!tabs[tab]) tab = 'mesas';
  const box = h('div');
  setScreen(
    restaurant.name,
    back,
    restaurant.address && h('p', { class: 'muted address' }, restaurant.address),
    tabBar(`#/u/${userId}/r/${restaurantId}`, TABS, tab),
    box,
  );
  await tabs[tab](restaurantId, box, isStale);
}

async function tabTables(restaurantId, box, isStale) {
  const list = h('ul', { class: 'list' });

  async function refresh() {
    const tables = await api(`/api/restaurants/${restaurantId}/tables`);
    if (isStale()) return;
    const rows = tables.map((table) =>
      h(
        'li',
        null,
        h('div', { class: 'row' }, h('strong', null, table.name), h('span', { class: 'muted' }, people(table.capacity))),
      ),
    );
    list.replaceChildren(...(rows.length ? rows : [empty('Este restaurante aún no tiene mesas. Añade la primera abajo.')]));
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api(`/api/restaurants/${restaurantId}/tables`, { method: 'POST', body: data });
        f.reset();
        toast('Mesa añadida');
        await refresh();
      }),
    },
    h('h2', null, 'Nueva mesa'),
    h(
      'div',
      { class: 'pair' },
      field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 40, placeholder: 'Mesa 1', autocomplete: 'off' })),
      field('Personas', h('input', { name: 'capacity', type: 'number', required: true, min: 1, max: 50, value: 4, inputmode: 'numeric' })),
    ),
    h('button', { class: 'btn', type: 'submit' }, 'Añadir mesa'),
  );

  box.append(list, form);
  await refresh();
}

async function tabMenu(restaurantId, box, isStale) {
  const holder = h('div');

  async function refresh() {
    const items = await api(`/api/restaurants/${restaurantId}/menu`);
    if (isStale()) return;
    holder.replaceChildren(menuList(items, 'El menú está vacío. Añade el primer plato abajo.'));
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api(`/api/restaurants/${restaurantId}/menu`, { method: 'POST', body: data });
        f.reset();
        toast('Añadido al menú');
        await refresh();
      }),
    },
    h('h2', null, 'Nuevo plato'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 120, autocomplete: 'off' })),
    field('Descripción (opcional)', h('input', { name: 'description', type: 'text', maxlength: 300, autocomplete: 'off' })),
    field('Precio (€)', h('input', { name: 'price', type: 'number', required: true, min: 0, step: '0.01', inputmode: 'decimal' })),
    h('button', { class: 'btn', type: 'submit' }, 'Añadir al menú'),
  );

  box.append(holder, form);
  await refresh();
}

/* Reservas de un día (y, si se elige, de una hora concreta), como un libro de reservas. */
async function tabReservations(restaurantId, box, isStale) {
  const date = h('input', { name: 'date', type: 'date', value: todayStr(), required: true });
  const time = timeSelect('', 'Todo el día');
  const list = h('ul', { class: 'list ledger' });
  let latest = 0;

  async function refresh() {
    if (!date.value) {
      latest++; // descarta cualquier consulta anterior que aún esté en curso
      list.replaceChildren(empty('Elige una fecha para ver las reservas.'));
      return;
    }
    const request = ++latest;
    const params = new URLSearchParams({ date: date.value });
    if (time.value) params.set('time', time.value);
    const reservations = await api(`/api/restaurants/${restaurantId}/reservations?${params}`);
    if (request !== latest || isStale()) return; // llegó tarde: el usuario ya cambió el filtro
    const rows = reservations.map((r) =>
      h(
        'li',
        { class: 'ledger-row' },
        h('div', { class: 'time' }, r.time),
        h('div', { class: 'what' }, h('strong', null, r.table), h('div', { class: 'muted' }, `Cliente: ${r.customer}`)),
      ),
    );
    list.replaceChildren(...(rows.length ? rows : [empty(time.value ? 'No hay reservas a esa hora.' : 'No hay reservas ese día.')]));
  }

  const reload = () => refresh().catch((err) => toast(err.message, true));
  date.addEventListener('change', reload);
  time.addEventListener('change', reload);

  box.append(h('div', { class: 'panel' }, h('div', { class: 'pair' }, field('Fecha', date), field('Hora', time))), list);
  await refresh();
}
