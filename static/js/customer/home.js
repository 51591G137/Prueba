/* Inicio de un cliente: pestañas «Restaurantes» y «Mis reservas». */
import { api } from '../core/api.js';
import { h, listOf, loading } from '../core/dom.js';
import { setScreen, tabBar } from '../core/ui.js';
import { bookingsTab } from './bookings.js';

const TABS = [
  ['restaurantes', 'Restaurantes'],
  ['reservas', 'Mis reservas'],
];
const TAB_VIEWS = { restaurantes: restaurantsTab, reservas: bookingsTab };

export async function viewCustomerHome({ params, stale }) {
  const { cid } = params;
  const tab = TAB_VIEWS[params.tab] ? params.tab : 'restaurantes';
  setScreen('Cargando…', '#/', loading());
  const customer = await api.get(`/api/customers/${cid}`);
  if (stale()) return;

  const box = h('div');
  setScreen(`Hola, ${customer.name}`, '#/', tabBar(`#/c/${cid}`, TABS, tab), box);
  await TAB_VIEWS[tab]({ cid, box, stale });
}

/* Todos los restaurantes dados de alta. */
async function restaurantsTab({ cid, box, stale }) {
  const restaurants = await api.get('/api/restaurants');
  if (stale()) return;
  const row = (restaurant) =>
    h(
      'li',
      null,
      h(
        'a',
        { class: 'row', href: `#/c/${cid}/r/${restaurant.id}/mesas` },
        h('div', { class: 'grow' }, h('strong', null, restaurant.name), restaurant.address && h('div', { class: 'muted small' }, restaurant.address)),
      ),
    );
  box.append(listOf(restaurants, row, 'Todavía no hay restaurantes. Vuelve más tarde.'));
}
