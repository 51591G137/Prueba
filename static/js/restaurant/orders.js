/* Formulario de comanda (nueva o edición): elegir platos y cantidades de una mesa. */
import { api } from '../core/api.js';
import { field, h, loading } from '../core/dom.js';
import { euro } from '../core/format.js';
import { leave } from '../core/router.js';
import { confirmDialog, guarded, onSubmit, setScreen, toast } from '../core/ui.js';
import { stepper } from '../components/stepper.js';
import { ORDER_STATUS } from './status.js';

export const viewOrderNew = (ctx) => orderForm(ctx, null);
export const viewOrderEdit = (ctx) => orderForm(ctx, ctx.params.oid);

async function orderForm({ params, stale }, orderId) {
  const { uid, rid, tid } = params;
  const back = `#/u/${uid}/r/${rid}/mesa/${tid}`;
  const title = orderId ? 'Editar comanda' : 'Nueva comanda';
  setScreen(title, back, loading());
  const [table, menu, order] = await Promise.all([
    api.get(`/api/tables/${tid}`),
    api.get(`/api/restaurants/${rid}/menu`),
    orderId ? api.get(`/api/orders/${orderId}`) : null,
  ]);
  if (stale()) return;

  const removeOrder = guarded(async () => {
    const confirmed = await confirmDialog({
      title: '¿Borrar la comanda?',
      message: 'No se puede deshacer.',
      confirmLabel: 'Borrar comanda',
      danger: true,
    });
    if (!confirmed) return;
    await api.del(`/api/orders/${order.id}`);
    toast('Comanda borrada');
    leave(back);
  });

  // Comandas que ya no se pueden modificar
  if (order && (order.bill_id || order.status === 'cancelado')) {
    setScreen(
      title,
      back,
      h(
        'div',
        { class: 'notice' },
        h('p', null, order.bill_id
          ? 'Esta comanda ya está en una factura. Anula la factura para poder modificarla.'
          : 'Esta comanda está cancelada: ya solo se puede borrar.'),
      ),
      !order.bill_id && h('button', { class: 'btn danger', type: 'button', onclick: removeOrder }, 'Borrar comanda'),
    );
    return;
  }

  if (!menu.length) {
    setScreen(
      title,
      back,
      h(
        'div',
        { class: 'notice info' },
        h('p', null, 'El menú de este restaurante está vacío. Añade platos para poder crear comandas.'),
        h('a', { class: 'btn', href: `#/u/${uid}/r/${rid}/menu` }, 'Ir al menú'),
      ),
    );
    return;
  }

  // Cantidades elegidas por plato. Los platos que ya estaban en la comanda conservan el precio con el que se pidieron.
  const quantities = new Map(order ? order.lines.filter((l) => l.item_id).map((l) => [l.item_id, l.quantity]) : []);
  const keptPrice = new Map(order ? order.lines.filter((l) => l.item_id).map((l) => [l.item_id, l.unit_price]) : []);
  const priceOf = (item) => keptPrice.get(item.id) ?? item.price;

  const totalEl = h('span', { class: 'total' });
  const submit = h('button', { class: 'btn', type: 'submit' }, order ? 'Guardar cambios' : 'Crear comanda');

  function repaint() {
    let cents = 0;
    let count = 0;
    for (const item of menu) {
      const quantity = quantities.get(item.id) || 0;
      count += quantity;
      cents += Math.round(priceOf(item) * 100) * quantity;
    }
    totalEl.textContent = euro.format(cents / 100);
    submit.disabled = count === 0;
  }

  const rows = menu.map((item) =>
    h(
      'li',
      null,
      h(
        'div',
        { class: 'pick' },
        h('div', { class: 'info' }, h('span', { class: 'dish' }, item.name), h('div', { class: 'muted small' }, euro.format(priceOf(item)))),
        stepper({
          value: quantities.get(item.id) || 0,
          label: item.name,
          onChange: (n) => {
            quantities.set(item.id, n);
            repaint();
          },
        }),
      ),
    ),
  );

  const form = h(
    'form',
    {
      onsubmit: onSubmit(async (data) => {
        const items = [...quantities].filter(([, quantity]) => quantity > 0).map(([item_id, quantity]) => ({ item_id, quantity }));
        const body = { user_id: uid, requests: data.requests, items };
        if (order) {
          await api.patch(`/api/orders/${order.id}`, { ...body, status: data.status });
        } else {
          await api.post(`/api/tables/${tid}/orders`, body);
        }
        toast(order ? 'Comanda actualizada' : 'Comanda creada');
        leave(back);
      }),
    },
    h('h2', null, `Platos para ${table.name}`),
    h('ul', { class: 'list' }, rows),
    h(
      'div',
      { class: 'panel' },
      field('Notas (opcional)', h('input', { name: 'requests', type: 'text', value: order?.requests || '', maxlength: 300, placeholder: 'Por ejemplo: sin sal, para compartir', autocomplete: 'off' })),
      order &&
        field(
          'Estado',
          h('select', { name: 'status', value: order.status }, Object.entries(ORDER_STATUS).map(([value, label]) => h('option', { value }, label))),
        ),
    ),
    h('div', { class: 'action-bar' }, h('div', null, h('div', { class: 'muted small' }, 'Total'), totalEl), submit),
  );

  setScreen(
    title,
    back,
    form,
    order && h('div', { class: 'danger-zone' }, h('button', { class: 'btn danger', type: 'button', onclick: removeOrder }, 'Borrar comanda')),
  );
  repaint();
}
