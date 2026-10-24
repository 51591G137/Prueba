'use strict';
/* App de restaurantes: usuario -> restaurantes -> mesas/menú/reservas/pagos.
   Rutas:
     #/                                  usuarios
     #/u/3                               restaurantes del usuario
     #/u/3/r/7/mesas|menu|reservas|pagos pestañas del restaurante
     #/u/3/r/7/mesas/5                   detalle de la mesa 5 (comandas)
*/

const TABS = [
  ['mesas', 'Mesas'],
  ['menu', 'Menú'],
  ['reservas', 'Reservas'],
  ['pagos', 'Pagos'],
];

startRouter((parts, isStale) => {
  const [a, userId, b, restaurantId, tab, tableId] = parts;
  if (a === 'u' && userId && b === 'r' && restaurantId && tab === 'mesas' && tableId) {
    return viewTable(userId, restaurantId, tableId, isStale);
  }
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

  const nameInput = h('input', { name: 'name', type: 'text', required: true, maxlength: 80, value: user.name });
  const editForm = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async () => {
        await api(`/api/users/${userId}`, { method: 'PATCH', body: { name: nameInput.value } });
        toast('Nombre actualizado');
      }),
    },
    h('h2', null, 'Editar nombre'),
    field('Nombre', nameInput),
    h('div', { class: 'actions' },
      h('button', { class: 'btn', type: 'submit' }, 'Guardar'),
      h('button', {
        class: 'btn danger', type: 'button',
        onclick: async () => {
          if (!confirm('¿Borrar este usuario? Solo es posible si no tiene restaurantes.')) return;
          try {
            await api(`/api/users/${userId}`, { method: 'DELETE' });
            toast('Usuario borrado');
            location.hash = '#/';
          } catch (err) { toast(err.message, true); }
        },
      }, 'Borrar usuario'),
    ),
  );

  const list = h('ul', { class: 'list' });

  async function refresh() {
    const restaurants = await api(`/api/users/${userId}/restaurants`);
    if (isStale()) return;
    const rows = restaurants.map((restaurant) =>
      h('li', null, h(
        'a',
        { class: 'row', href: `#/u/${userId}/r/${restaurant.id}/mesas` },
        h('div', { class: 'grow' }, h('strong', null, restaurant.name),
          restaurant.address && h('div', { class: 'muted small' }, restaurant.address)),
      )),
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

  setScreen(`Hola, ${user.name}`, '#/', editForm, h('h2', null, 'Tus restaurantes'), list, form);
  await refresh();
}

/* ---------- Un restaurante ---------- */

async function viewRestaurant(userId, restaurantId, tab, isStale) {
  const back = `#/u/${userId}`;
  setScreen('Cargando…', back, loading());
  const restaurant = await api(`/api/restaurants/${restaurantId}`);
  if (isStale()) return;

  const tabs = { mesas: tabTables, menu: tabMenu, reservas: tabReservations, pagos: tabPaymentMethods };
  if (!tabs[tab]) tab = 'mesas';
  const box = h('div');
  setScreen(
    restaurant.name,
    back,
    restaurant.address && h('p', { class: 'muted address' }, restaurant.address),
    tabBar(`#/u/${userId}/r/${restaurantId}`, TABS, tab),
    box,
  );
  await tabs[tab](userId, restaurantId, box, isStale);
}

/* ---------- Mesas ---------- */

async function tabTables(userId, restaurantId, box, isStale) {
  const list = h('ul', { class: 'list' });

  async function refresh() {
    const tables = await api(`/api/restaurants/${restaurantId}/tables`);
    if (isStale()) return;
    const rows = tables.map((table) => {
      const badge = h('span', {
        class: table.status === 'occupied' ? 'badge occupied' : 'badge free',
      }, table.status === 'occupied' ? 'Ocupada' : 'Libre');
      return h('li', null, h(
        'div',
        { class: 'row' },
        h('div', { class: 'grow' },
          h('a', { href: `#/u/${userId}/r/${restaurantId}/mesas/${table.id}` },
            h('strong', null, table.name)),
          h('div', { class: 'muted small' }, people(table.capacity)),
        ),
        badge,
        h('div', { class: 'actions' },
          h('a', { class: 'btn small', href: `#/u/${userId}/r/${restaurantId}/mesas/${table.id}` }, 'Comandas'),
          h('button', {
            class: 'btn small ghost', type: 'button',
            onclick: async () => { await editTable(table); },
          }, 'Editar'),
          h('button', {
            class: 'btn small danger', type: 'button',
            onclick: async () => {
              if (!confirm(`¿Borrar la mesa "${table.name}"?`)) return;
              try {
                await api(`/api/restaurants/${restaurantId}/tables/${table.id}`, { method: 'DELETE' });
                toast('Mesa borrada');
                await refresh();
              } catch (err) { toast(err.message, true); }
            },
          }, 'Borrar'),
        ),
      ));
    });
    list.replaceChildren(...(rows.length ? rows : [empty('Este restaurante aún no tiene mesas. Añade la primera abajo.')]));
  }

  async function editTable(table) {
    const newName = prompt('Nuevo nombre para la mesa:', table.name);
    if (newName === null) return;
    const newCap = prompt('Nueva capacidad (personas):', String(table.capacity));
    if (newCap === null) return;
    try {
      await api(`/api/restaurants/${restaurantId}/tables/${table.id}`, {
        method: 'PATCH',
        body: { name: newName, capacity: Number(newCap) },
      });
      toast('Mesa actualizada');
      await refresh();
    } catch (err) { toast(err.message, true); }
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
    h('div', { class: 'pair' },
      field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 40, placeholder: 'Mesa 1', autocomplete: 'off' })),
      field('Personas', h('input', { name: 'capacity', type: 'number', required: true, min: 1, max: 50, value: 4, inputmode: 'numeric' })),
    ),
    h('button', { class: 'btn', type: 'submit' }, 'Añadir mesa'),
  );

  box.append(list, form);
  await refresh();
}

/* ---------- Detalle de una mesa: comandas y cobro ---------- */

async function viewTable(userId, restaurantId, tableId, isStale) {
  const back = `#/u/${userId}/r/${restaurantId}/mesas`;
  setScreen('Cargando…', back, loading());

  const [table, menu, methods] = await Promise.all([
    api(`/api/restaurants/${restaurantId}/tables`).then(
      (ts) => ts.find((t) => String(t.id) === String(tableId)),
    ),
    api(`/api/restaurants/${restaurantId}/menu`),
    api(`/api/restaurants/${restaurantId}/payment-methods`),
  ]);
  if (isStale()) return;
  if (!table) { showError(new Error('Mesa no encontrada.')); return; }

  const box = h('div');
  setScreen(
    `${table.name} · ${table.status === 'occupied' ? 'Ocupada' : 'Libre'}`,
    back,
    table ? h('p', { class: 'muted address' }, people(table.capacity)) : null,
    box,
  );
  await renderTableContent(userId, restaurantId, table, menu, methods, box, isStale);
}

async function renderTableContent(userId, restaurantId, table, menu, methods, box, isStale) {
  const orders = await api(`/api/restaurants/${restaurantId}/orders?table_id=${table.id}&active=true`);
  if (isStale()) return;

  if (!menu.length) {
    box.append(h('div', { class: 'notice' },
      h('p', null, 'Añade platos al menú antes de crear comandas.'),
      h('a', { class: 'btn', href: `#/u/${userId}/r/${restaurantId}/menu` }, 'Ir al menú'),
    ));
    return;
  }

  const ordersBox = h('div');
  const totals = { total: 0 };
  orders.forEach((o) => {
    ordersBox.append(renderOrder(o, restaurantId, menu, () => refreshAll()));
    totals.total += o.total;
  });

  const payBox = h('div');
  if (orders.length) {
    const select = h('select', { name: 'payment_method_id', required: true },
      h('option', { value: '' }, '— Método de pago —'),
      ...methods.map((m) => h('option', { value: String(m.id) }, m.name)),
    );
    if (!methods.length) {
      payBox.append(h('div', { class: 'notice' },
        h('p', null, 'Para cobrar necesitas al menos un método de pago.'),
        h('a', { class: 'btn', href: `#/u/${userId}/r/${restaurantId}/pagos` }, 'Crear método de pago'),
      ));
    } else {
      payBox.append(h('form', {
        class: 'panel',
        onsubmit: onSubmit(async (data) => {
          await api(`/api/tables/${table.id}/bill`, {
            method: 'POST',
            body: { payment_method_id: Number(data.payment_method_id) },
          });
          toast('Factura pagada. Mesa liberada.');
          await refreshAll();
        }),
      },
        h('h2', null, `Cobrar mesa — total ${euro.format(totals.total)}`),
        field('Método de pago', select),
        h('button', { class: 'btn', type: 'submit' }, 'Emitir factura y cobrar'),
      ));
    }
  }

  const newOrderForm = renderNewOrderForm(restaurantId, table.id, menu, () => refreshAll());

  box.replaceChildren(ordersBox, newOrderForm, payBox);

  async function refreshAll() {
    const [freshTable, freshOrders] = await Promise.all([
      api(`/api/restaurants/${restaurantId}/tables`).then((ts) => ts.find((t) => t.id === table.id)),
      api(`/api/restaurants/${restaurantId}/orders?table_id=${table.id}&active=true`),
    ]);
    if (isStale()) return;
    table = freshTable || table;
    $('#title').textContent = `${table.name} · ${table.status === 'occupied' ? 'Ocupada' : 'Libre'}`;
    await renderTableContent(userId, restaurantId, table, menu, methods, box, isStale);
  }
}

function renderOrder(order, restaurantId, menu, onChange) {
  const itemsList = h('ul', { class: 'list compact' },
    ...order.items.map((oi) => h('li', null,
      h('div', { class: 'item-row' },
        h('div', { class: 'grow' },
          h('strong', null, `${oi.quantity}× ${oi.name || 'Plato eliminado'}`),
          oi.requests && h('div', { class: 'muted small' }, oi.requests),
        ),
        h('span', { class: 'price' }, euro.format(oi.subtotal)),
        h('button', {
          class: 'btn small ghost', type: 'button',
          onclick: async () => {
            const q = prompt('Nueva cantidad:', String(oi.quantity));
            if (q === null) return;
            try {
              await api(`/api/orders/${order.id}/items/${oi.id}`, {
                method: 'PATCH', body: { quantity: Number(q) },
              });
              await onChange();
            } catch (err) { toast(err.message, true); }
          },
        }, '✎'),
        h('button', {
          class: 'btn small danger', type: 'button',
          onclick: async () => {
            if (!confirm('¿Quitar este plato de la comanda?')) return;
            try {
              await api(`/api/orders/${order.id}/items/${oi.id}`, { method: 'DELETE' });
              await onChange();
            } catch (err) { toast(err.message, true); }
          },
        }, '×'),
      ),
    )),
  );

  const addSelect = h('select', null,
    h('option', { value: '' }, '— Añadir plato —'),
    ...menu.map((m) => h('option', { value: String(m.id) }, `${m.name} · ${euro.format(m.price)}`)),
  );
  const addQty = h('input', { type: 'number', min: 1, max: 99, value: 1, inputmode: 'numeric' });
  const addForm = h('div', { class: 'inline-form' },
    addSelect, addQty,
    h('button', {
      class: 'btn small', type: 'button',
      onclick: async () => {
        if (!addSelect.value) { toast('Elige un plato.', true); return; }
        try {
          await api(`/api/orders/${order.id}/items`, {
            method: 'POST',
            body: { item_id: Number(addSelect.value), quantity: Number(addQty.value) },
          });
          await onChange();
        } catch (err) { toast(err.message, true); }
      },
    }, 'Añadir'),
  );

  const actions = h('div', { class: 'actions' },
    h('button', {
      class: 'btn small danger', type: 'button',
      onclick: async () => {
        if (!confirm(`¿Cancelar la comanda #${order.id}?`)) return;
        try {
          await api(`/api/orders/${order.id}`, { method: 'DELETE' });
          await onChange();
        } catch (err) { toast(err.message, true); }
      },
    }, 'Cancelar comanda'),
  );

  return h('div', { class: 'panel' },
    h('div', { class: 'order-head' },
      h('strong', null, `Comanda #${order.id}`),
      h('span', { class: 'muted small' }, order.status),
    ),
    itemsList,
    addForm,
    actions,
  );
}

function renderNewOrderForm(restaurantId, tableId, menu, onChange) {
  const cart = [];
  const cartList = h('ul', { class: 'list compact' });
  const select = h('select', null,
    h('option', { value: '' }, '— Elegir plato —'),
    ...menu.map((m) => h('option', { value: String(m.id) }, `${m.name} · ${euro.format(m.price)}`)),
  );
  const qty = h('input', { type: 'number', min: 1, max: 99, value: 1, inputmode: 'numeric' });

  function renderCart() {
    if (!cart.length) {
      cartList.replaceChildren(empty('Aún no has añadido platos.'));
      return;
    }
    cartList.replaceChildren(...cart.map((c, i) => h('li', null,
      h('div', { class: 'item-row' },
        h('div', { class: 'grow' }, h('strong', null, `${c.quantity}× ${c.name}`)),
        h('span', { class: 'price' }, euro.format(c.quantity * c.price)),
        h('button', {
          class: 'btn small danger', type: 'button',
          onclick: () => { cart.splice(i, 1); renderCart(); },
        }, '×'),
      ),
    )));
  }
  renderCart();

  const form = h('form', {
    class: 'panel',
    onsubmit: onSubmit(async (data, f) => {
      if (!cart.length) { toast('Añade al menos un plato.', true); return; }
      await api(`/api/restaurants/${restaurantId}/orders`, {
        method: 'POST',
        body: {
          table_id: tableId,
          requests: data.requests || undefined,
          items: cart.map((c) => ({ item_id: c.item_id, quantity: c.quantity })),
        },
      });
      toast('Comanda enviada');
      await onChange();
    }),
  },
    h('h2', null, 'Nueva comanda'),
    h('div', { class: 'inline-form' },
      select, qty,
      h('button', {
        class: 'btn small', type: 'button',
        onclick: () => {
          if (!select.value) { toast('Elige un plato.', true); return; }
          const opt = menu.find((m) => String(m.id) === select.value);
          cart.push({ item_id: opt.id, name: opt.name, price: opt.price, quantity: Number(qty.value) });
          select.value = '';
          qty.value = 1;
          renderCart();
        },
      }, 'Añadir'),
    ),
    cartList,
    field('Peticiones generales (opcional)',
      h('input', { name: 'requests', type: 'text', maxlength: 300, autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Enviar comanda'),
  );
  return form;
}

/* ---------- Menú ---------- */

async function tabMenu(userId, restaurantId, box, isStale) {
  const holder = h('div');
  let menu = [];

  async function refresh() {
    menu = await api(`/api/restaurants/${restaurantId}/menu`);
    if (isStale()) return;
    if (!menu.length) {
      holder.replaceChildren(h('ul', { class: 'list' }, empty('El menú está vacío. Añade el primer plato abajo.')));
      return;
    }
    holder.replaceChildren(h('ul', { class: 'list' }, ...menu.map((item) => h('li', null,
      h('div', { class: 'row' },
        h('div', { class: 'grow' },
          h('strong', null, item.name),
          item.description && h('div', { class: 'muted small' }, item.description),
        ),
        h('span', { class: 'price' }, euro.format(item.price)),
        h('button', {
          class: 'btn small ghost', type: 'button',
          onclick: async () => {
            const name = prompt('Nombre:', item.name);
            if (name === null) return;
            const desc = prompt('Descripción:', item.description || '');
            if (desc === null) return;
            const price = prompt('Precio (€):', String(item.price));
            if (price === null) return;
            try {
              await api(`/api/restaurants/${restaurantId}/menu/${item.id}`, {
                method: 'PATCH',
                body: { name, description: desc || null, price: Number(price) },
              });
              toast('Plato actualizado');
              await refresh();
            } catch (err) { toast(err.message, true); }
          },
        }, 'Editar'),
        h('button', {
          class: 'btn small danger', type: 'button',
          onclick: async () => {
            if (!confirm(`¿Borrar "${item.name}" del menú?`)) return;
            try {
              await api(`/api/restaurants/${restaurantId}/menu/${item.id}`, { method: 'DELETE' });
              toast('Plato borrado');
              await refresh();
            } catch (err) { toast(err.message, true); }
          },
        }, 'Borrar'),
      ),
    ))));
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

/* ---------- Reservas ---------- */

async function tabReservations(userId, restaurantId, box, isStale) {
  const date = h('input', { name: 'date', type: 'date', value: todayStr(), required: true });
  const time = timeSelect('', 'Todo el día');
  const list = h('ul', { class: 'list ledger' });
  let latest = 0;

  async function refresh() {
    if (!date.value) { latest++; list.replaceChildren(empty('Elige una fecha para ver las reservas.')); return; }
    const request = ++latest;
    const params = new URLSearchParams({ date: date.value });
    if (time.value) params.set('time', time.value);
    const reservations = await api(`/api/restaurants/${restaurantId}/reservations?${params}`);
    if (request !== latest || isStale()) return;
    const rows = reservations.map((r) =>
      h('li', { class: 'ledger-row' },
        h('div', { class: 'time' }, r.time),
        h('div', { class: 'what' },
          h('strong', null, r.table),
          h('div', { class: 'muted' }, `Cliente: ${r.customer}`),
        ),
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

/* ---------- Métodos de pago ---------- */

async function tabPaymentMethods(userId, restaurantId, box, isStale) {
  const list = h('ul', { class: 'list' });

  async function refresh() {
    const methods = await api(`/api/restaurants/${restaurantId}/payment-methods`);
    if (isStale()) return;
    const rows = methods.map((m) => h('li', null,
      h('div', { class: 'row' },
        h('strong', { class: 'grow' }, m.name),
        h('button', {
          class: 'btn small ghost', type: 'button',
          onclick: async () => {
            const name = prompt('Nombre del método de pago:', m.name);
            if (name === null) return;
            try {
              await api(`/api/restaurants/${restaurantId}/payment-methods/${m.id}`, {
                method: 'PATCH', body: { name },
              });
              toast('Método actualizado');
              await refresh();
            } catch (err) { toast(err.message, true); }
          },
        }, 'Editar'),
        h('button', {
          class: 'btn small danger', type: 'button',
          onclick: async () => {
            if (!confirm(`¿Borrar "${m.name}"?`)) return;
            try {
              await api(`/api/restaurants/${restaurantId}/payment-methods/${m.id}`, { method: 'DELETE' });
              toast('Método borrado');
              await refresh();
            } catch (err) { toast(err.message, true); }
          },
        }, 'Borrar'),
      ),
    ));
    list.replaceChildren(...(rows.length ? rows : [empty('Aún no hay métodos de pago. Añade el primero abajo.')]));
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api(`/api/restaurants/${restaurantId}/payment-methods`, { method: 'POST', body: data });
        f.reset();
        toast('Método añadido');
        await refresh();
      }),
    },
    h('h2', null, 'Nuevo método de pago'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 60, placeholder: 'Efectivo, Tarjeta, Bizum…', autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Añadir método'),
  );

  box.append(h('h2', null, 'Métodos de pago'), list, form);
  await refresh();
}