/* Un restaurante visto por un cliente: mesas con reserva y menú. */
import { api } from '../core/api.js';
import { empty, fill, h, loading } from '../core/dom.js';
import { formatDate, people } from '../core/format.js';
import { setScreen, tabBar, toast } from '../core/ui.js';
import { menuList } from '../components/menu-list.js';
import { whenPanel } from '../components/when-panel.js';

const TABS = [
  ['mesas', 'Mesas'],
  ['menu', 'Menú'],
];
const TAB_VIEWS = { mesas: tablesTab, menu: menuTab };

export async function viewRestaurant({ params, stale }) {
  const { cid, rid } = params;
  const tab = TAB_VIEWS[params.tab] ? params.tab : 'mesas';
  const back = `#/c/${cid}`;
  setScreen('Cargando…', back, loading());
  const restaurant = await api.get(`/api/restaurants/${rid}`);
  if (stale()) return;

  const box = h('div');
  setScreen(
    restaurant.name,
    back,
    restaurant.address && h('p', { class: 'muted address' }, restaurant.address),
    tabBar(`#/c/${cid}/r/${rid}`, TABS, tab),
    box,
  );
  await TAB_VIEWS[tab]({ cid, rid, box, stale });
}

/* Se elige fecha y hora, se ven las mesas libres y reservadas en esa franja y se reserva. */
async function tablesTab({ cid, rid, box, stale }) {
  const list = h('ul', { class: 'list' });
  let latest = 0;

  async function refresh() {
    if (!when.date.value) {
      latest++; // descarta cualquier consulta anterior que aún esté en curso
      list.removeAttribute('aria-busy');
      list.replaceChildren(empty('Elige una fecha para ver las mesas libres.'));
      return;
    }
    const request = ++latest;
    // Mientras se recarga, la lista se atenúa y no admite toques: así nunca se reserva
    // una mesa de la lista antigua con la fecha u hora nuevas.
    list.setAttribute('aria-busy', 'true');
    let tables;
    try {
      const params = new URLSearchParams({ date: when.date.value, time: when.time.value });
      tables = await api.get(`/api/restaurants/${rid}/tables?${params}`);
    } finally {
      if (request === latest) list.removeAttribute('aria-busy');
    }
    if (request !== latest || stale()) return; // llegó tarde: ya se cambió la fecha u hora
    fill(
      list,
      tables,
      (table) =>
        h(
          'li',
          null,
          h(
            'div',
            { class: table.reserved ? 'row taken' : 'row' },
            h('div', { class: 'grow' }, h('strong', null, table.name), h('div', { class: 'muted small' }, people(table.capacity))),
            table.reserved
              ? h('span', { class: 'status' }, 'Reservada')
              : h('button', { class: 'btn small', type: 'button', onclick: (event) => reserve(table, event.currentTarget) }, 'Reservar'),
          ),
        ),
      'Este restaurante aún no ha añadido mesas.',
    );
  }

  async function reserve(table, button) {
    button.disabled = true;
    try {
      await api.post('/api/reservations', { customer_id: cid, table_id: table.id, date: when.date.value, time: when.time.value });
      toast(`Reserva confirmada: ${table.name}, ${formatDate(when.date.value)} a las ${when.time.value}.`);
    } catch (err) {
      toast(err.message, true);
    }
    await refresh().catch((err) => toast(err.message, true)); // actualiza el estado de las mesas en ambos casos
  }

  const when = whenPanel({ onChange: () => refresh().catch((err) => toast(err.message, true)) });
  box.append(when.panel, list);
  await refresh();
}

async function menuTab({ rid, box, stale }) {
  const items = await api.get(`/api/restaurants/${rid}/menu`);
  if (stale()) return;
  box.append(menuList(items, 'Este restaurante aún no ha publicado su menú.'));
}
