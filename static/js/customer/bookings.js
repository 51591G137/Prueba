/* Mis reservas: ver las próximas, cambiarlas (fecha, hora o mesa) y cancelarlas. */
import { api } from '../core/api.js';
import { field, fill, h, loading } from '../core/dom.js';
import { formatDate, people, todayStr } from '../core/format.js';
import { leave } from '../core/router.js';
import { confirmDialog, guarded, onSubmit, setScreen, toast } from '../core/ui.js';
import { whenPanel } from '../components/when-panel.js';

const cancelDialog = (r) =>
  confirmDialog({
    title: '¿Cancelar la reserva?',
    message: `${r.restaurant}, ${r.table}, el ${formatDate(r.date)} a las ${r.time}.`,
    confirmLabel: 'Cancelar reserva',
    danger: true,
  });

export async function bookingsTab({ cid, box, stale }) {
  const list = h('ul', { class: 'list' });

  async function refresh() {
    const reservations = await api.get(`/api/customers/${cid}/reservations?from=${todayStr()}`);
    if (stale()) return;
    fill(list, reservations, row, 'No tienes reservas próximas. Reserva una mesa en la pestaña Restaurantes.');
  }

  const cancel = (reservation) =>
    guarded(async () => {
      if (!(await cancelDialog(reservation))) return;
      await api.del(`/api/reservations/${reservation.id}`);
      toast('Reserva cancelada');
      await refresh();
    });

  const row = (r) =>
    h(
      'li',
      { class: 'booking' },
      h(
        'div',
        null,
        h('p', { class: 'when' }, `${formatDate(r.date)} a las ${r.time}`),
        h('strong', null, r.restaurant),
        h('div', { class: 'muted small' }, `${r.table}, ${people(r.capacity)}`),
      ),
      h(
        'div',
        { class: 'btns' },
        h('a', { class: 'btn small', href: `#/c/${cid}/reserva/${r.id}` }, 'Cambiar'),
        h('button', { class: 'btn small danger-outline', type: 'button', onclick: cancel(r) }, 'Cancelar reserva'),
      ),
    );

  box.append(list);
  await refresh();
}

export async function viewReservationEdit({ params, stale }) {
  const { cid, resid } = params;
  const back = `#/c/${cid}/reservas`;
  setScreen('Cambiar reserva', back, loading());
  const reservation = await api.get(`/api/reservations/${resid}`);
  if (stale()) return;

  const tableSelect = h('select', { name: 'table_id' });
  const submit = h('button', { class: 'btn', type: 'submit' }, 'Guardar cambios');
  const note = h('p', { class: 'muted small' });
  let latest = 0;

  // Mesas del restaurante para la fecha y hora elegidas. La propia reserva no cuenta como ocupada.
  async function loadTables() {
    const request = ++latest;
    if (!when.date.value) {
      tableSelect.replaceChildren();
      submit.disabled = true;
      note.textContent = 'Elige una fecha.';
      return;
    }
    const params = new URLSearchParams({ date: when.date.value, time: when.time.value, exclude_reservation: resid });
    const tables = await api.get(`/api/restaurants/${reservation.restaurant_id}/tables?${params}`);
    if (request !== latest || stale()) return;
    const wanted = tableSelect.value || String(reservation.table_id);
    tableSelect.replaceChildren(
      ...tables.map((t) =>
        h('option', { value: t.id, disabled: t.reserved }, `${t.name} (${people(t.capacity)})${t.reserved ? ', reservada' : ''}`),
      ),
    );
    const free = tables.filter((t) => !t.reserved);
    const keep = free.find((t) => String(t.id) === wanted) || free[0];
    if (keep) tableSelect.value = String(keep.id);
    submit.disabled = !keep;
    note.textContent = keep ? '' : 'No queda ninguna mesa libre en esa franja. Prueba con otra fecha u hora.';
  }

  const when = whenPanel({
    date: reservation.date,
    time: reservation.time,
    min: reservation.date < todayStr() ? reservation.date : todayStr(),
    onChange: () => loadTables().catch((err) => toast(err.message, true)),
  });

  const form = h(
    'form',
    {
      onsubmit: onSubmit(async (data) => {
        await api.patch(`/api/reservations/${resid}`, { date: data.date, time: data.time, table_id: data.table_id });
        toast('Reserva actualizada');
        leave(back);
      }),
    },
    h('h2', null, reservation.restaurant),
    when.panel,
    h('div', { class: 'panel' }, field('Mesa', tableSelect), note, submit),
  );

  const cancel = guarded(async () => {
    if (!(await cancelDialog(reservation))) return;
    await api.del(`/api/reservations/${resid}`);
    toast('Reserva cancelada');
    leave(back);
  });

  setScreen(
    'Cambiar reserva',
    back,
    form,
    h('div', { class: 'danger-zone' }, h('button', { class: 'btn danger-outline', type: 'button', onclick: cancel }, 'Cancelar reserva')),
  );
  await loadTables();
}
