/* Un restaurante: cabecera y pestañas. Cada pestaña vive en su propio archivo. */
import { api } from '../core/api.js';
import { h, loading } from '../core/dom.js';
import { setScreen, tabBar } from '../core/ui.js';
import { menuTab } from './menu.js';
import { paymentsTab } from './payments.js';
import { reservationsTab } from './reservations.js';
import { tablesTab } from './tables.js';

const TABS = [
  ['mesas', 'Mesas'],
  ['menu', 'Menú'],
  ['reservas', 'Reservas'],
  ['cobros', 'Cobros'],
];
const TAB_VIEWS = { mesas: tablesTab, menu: menuTab, reservas: reservationsTab, cobros: paymentsTab };

export async function viewRestaurant({ params, stale }) {
  const { uid, rid } = params;
  const tab = TAB_VIEWS[params.tab] ? params.tab : 'mesas';
  const back = `#/u/${uid}`;
  setScreen('Cargando…', back, loading());
  const restaurant = await api.get(`/api/restaurants/${rid}`);
  if (stale()) return;

  const box = h('div');
  setScreen(
    restaurant.name,
    back,
    restaurant.address && h('p', { class: 'muted address' }, restaurant.address),
    tabBar(`#/u/${uid}/r/${rid}`, TABS, tab),
    box,
  );
  await TAB_VIEWS[tab]({ uid, rid, box, stale });
}
