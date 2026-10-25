/* Una mesa: sus comandas sin cobrar, crear comandas y emitir la factura. */
import { api } from '../core/api.js';
import { h, listOf, loading, replace } from '../core/dom.js';
import { euro, formatTime, people } from '../core/format.js';
import { navigate } from '../core/router.js';
import { confirmDialog, guarded, setScreen, toast } from '../core/ui.js';
import { orderChip, tableChip } from './status.js';

export async function viewTableDetail({ params, stale }) {
  const { uid, rid, tid } = params;
  const back = `#/u/${uid}/r/${rid}/mesas`;
  const base = `#/u/${uid}/r/${rid}/mesa/${tid}`;
  setScreen('Cargando…', back, loading());

  const box = h('div');
  let shown = false;

  async function refresh() {
    const [table, orders] = await Promise.all([api.get(`/api/tables/${tid}`), api.get(`/api/tables/${tid}/orders`)]);
    if (stale()) return;
    if (!shown) {
      setScreen(table.name, back, box);
      shown = true;
    }
    paint(table, orders);
  }

  const removeOrder = (order) =>
    guarded(async () => {
      const confirmed = await confirmDialog({
        title: '¿Borrar la comanda?',
        message: `Se quitará la comanda de las ${formatTime(order.created_at)} (${euro.format(order.total)}). No se puede deshacer.`,
        confirmLabel: 'Borrar comanda',
        danger: true,
      });
      if (!confirmed) return;
      await api.del(`/api/orders/${order.id}`);
      toast('Comanda borrada');
      await refresh();
    });

  const issueBill = guarded(async () => {
    const bill = await api.post(`/api/tables/${tid}/bills`, { user_id: uid });
    navigate(`#/u/${uid}/r/${rid}/factura/${bill.id}`);
  });

  const orderRow = (order) =>
    h(
      'li',
      { class: 'order' },
      h(
        'div',
        { class: 'order-head' },
        h('span', { class: 'time' }, formatTime(order.created_at)),
        orderChip(order.status),
        order.bill_id && h('span', { class: 'chip warn' }, 'En factura'),
      ),
      h(
        'ul',
        { class: 'lines' },
        order.lines.map((line) =>
          h('li', null, h('span', null, `${line.quantity} × ${line.name}`), h('span', { class: 'amount' }, euro.format(line.subtotal))),
        ),
      ),
      order.requests && h('p', { class: 'muted small' }, `Notas: ${order.requests}`),
      h(
        'div',
        { class: 'order-foot' },
        h('strong', { class: 'amount' }, euro.format(order.total)),
        !order.bill_id &&
          h(
            'span',
            { class: 'btns' },
            h('a', { class: 'btn small secondary', href: `${base}/comanda/${order.id}` }, 'Editar'),
            h('button', { class: 'btn small danger-outline', type: 'button', onclick: removeOrder(order) }, 'Borrar'),
          ),
      ),
    );

  function paint(table, orders) {
    const pending = table.pending_bill;
    const billable = orders.filter((order) => !order.bill_id && order.status !== 'cancelado');
    const billableCents = billable.reduce((sum, order) => sum + Math.round(order.total * 100), 0);
    replace(
      box,
      h('p', { class: 'summary' }, tableChip(table.status), h('span', { class: 'muted' }, people(table.capacity))),
      pending &&
        h(
          'div',
          { class: 'notice info' },
          h('p', null, `Esta mesa tiene una factura pendiente de cobro: ${euro.format(pending.total)}.`),
          h('a', { class: 'btn', href: `#/u/${uid}/r/${rid}/factura/${pending.id}` }, 'Ver factura y cobrar'),
        ),
      h('h2', null, 'Comandas'),
      listOf(orders, orderRow, 'No hay comandas. Cuando la mesa pida algo, crea una comanda.'),
      h(
        'div',
        { class: 'actions' },
        pending
          ? h('button', { class: 'btn', type: 'button', disabled: true }, 'Nueva comanda')
          : h('a', { class: 'btn', href: `${base}/comanda/nueva` }, 'Nueva comanda'),
        h(
          'button',
          { class: 'btn secondary', type: 'button', disabled: pending || !billable.length, onclick: issueBill },
          billable.length ? `Emitir factura (${euro.format(billableCents / 100)})` : 'Emitir factura',
        ),
      ),
      pending && h('p', { class: 'muted small' }, 'Mientras haya una factura pendiente no se pueden añadir ni modificar comandas. Cóbrala o anúlala.'),
    );
  }

  await refresh();
}
