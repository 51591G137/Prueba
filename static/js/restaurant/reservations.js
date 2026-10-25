/* Reservas del restaurante: las de un día (y, si se elige, de una hora), como un libro de reservas. */
import { api } from '../core/api.js';
import { empty, fill, h } from '../core/dom.js';
import { toast } from '../core/ui.js';
import { whenPanel } from '../components/when-panel.js';

export async function reservationsTab({ rid, box, stale }) {
  const list = h('ul', { class: 'list' });
  let latest = 0;

  async function refresh() {
    if (!when.date.value) {
      latest++; // descarta cualquier consulta anterior que aún esté en curso
      list.replaceChildren(empty('Elige una fecha para ver las reservas.'));
      return;
    }
    const request = ++latest;
    const params = new URLSearchParams({ date: when.date.value });
    if (when.time.value) params.set('time', when.time.value);
    const reservations = await api.get(`/api/restaurants/${rid}/reservations?${params}`);
    if (request !== latest || stale()) return; // llegó tarde: ya se cambió el filtro
    fill(
      list,
      reservations,
      (r) =>
        h(
          'li',
          { class: 'ledger-row' },
          h('div', { class: 'time' }, r.time),
          h('div', { class: 'what' }, h('strong', null, r.table), h('div', { class: 'muted' }, `Cliente: ${r.customer}`)),
        ),
      when.time.value ? 'No hay reservas a esa hora.' : 'No hay reservas ese día.',
    );
  }

  const when = whenPanel({
    time: '',
    min: null,
    allTimesLabel: 'Todo el día',
    onChange: () => refresh().catch((err) => toast(err.message, true)),
  });

  box.append(when.panel, list);
  await refresh();
}
