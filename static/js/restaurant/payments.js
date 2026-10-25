/* Cobros: lista de facturas, métodos de pago, y la pantalla de una factura (cobrar o anular). */
import { api } from '../core/api.js';
import { field, fill, h, loading } from '../core/dom.js';
import { euro, formatDateTime } from '../core/format.js';
import { navigate } from '../core/router.js';
import { confirmDialog, guarded, onSubmit, setScreen, toast } from '../core/ui.js';

export async function paymentsTab({ uid, rid, box, stale }) {
  const bills = h('ul', { class: 'list' });
  const methods = h('ul', { class: 'list' });

  async function refreshBills() {
    const rows = await api.get(`/api/restaurants/${rid}/bills`);
    if (stale()) return;
    fill(
      bills,
      rows,
      (bill) =>
        h(
          'li',
          null,
          h(
            'a',
            { class: 'row', href: `#/u/${uid}/r/${rid}/factura/${bill.id}` },
            h('div', { class: 'grow' }, h('strong', null, bill.table), h('div', { class: 'muted small' }, formatDateTime(bill.open_datetime))),
            h(
              'div',
              { class: 'right' },
              h('strong', { class: 'amount' }, euro.format(bill.total)),
              bill.status === 'pendiente'
                ? h('div', null, h('span', { class: 'chip warn' }, 'Pendiente de cobro'))
                : h('div', { class: 'muted small' }, `Pagada con ${bill.payment_method || '¿?'}`),
            ),
          ),
        ),
      'Todavía no hay facturas. Aparecerán aquí cuando emitas la primera desde una mesa.',
    );
  }

  async function refreshMethods() {
    const rows = await api.get(`/api/restaurants/${rid}/payment-methods`);
    if (stale()) return;
    fill(
      methods,
      rows,
      (method) => h('li', null, h('div', { class: 'row' }, h('strong', null, method.name))),
      'No hay métodos de pago. Añade al menos uno (efectivo, tarjeta, bizum…) para poder cobrar.',
    );
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api.post(`/api/restaurants/${rid}/payment-methods`, data);
        f.reset();
        toast('Método de pago añadido');
        await refreshMethods();
      }),
    },
    h('h2', null, 'Nuevo método de pago'),
    field(
      'Nombre',
      h('input', { name: 'name', type: 'text', required: true, maxlength: 60, list: 'method-suggestions', placeholder: 'Efectivo, tarjeta, bizum…', autocomplete: 'off' }),
    ),
    h('datalist', { id: 'method-suggestions' }, ['Efectivo', 'Tarjeta', 'Bizum', 'Transferencia'].map((value) => h('option', { value }))),
    h('button', { class: 'btn', type: 'submit' }, 'Añadir método de pago'),
  );

  box.append(h('h2', null, 'Facturas'), bills, h('h2', null, 'Métodos de pago'), methods, form);
  await Promise.all([refreshBills(), refreshMethods()]);
}

export async function viewBill({ params, stale }) {
  const { uid, rid, bid } = params;
  const paymentsHash = `#/u/${uid}/r/${rid}/cobros`;
  setScreen('Factura', paymentsHash, loading());
  const [bill, methods] = await Promise.all([api.get(`/api/bills/${bid}`), api.get(`/api/restaurants/${rid}/payment-methods`)]);
  if (stale()) return;

  const pending = bill.status === 'pendiente';
  const tableHash = bill.table_id ? `#/u/${uid}/r/${rid}/mesa/${bill.table_id}` : paymentsHash;
  const back = pending ? tableHash : paymentsHash;

  const ticket = h(
    'div',
    { class: 'ticket' },
    h('p', { class: 'muted small' }, `${bill.table}, ${formatDateTime(bill.open_datetime)}`),
    h(
      'ul',
      { class: 'carta' },
      bill.lines.map((line) =>
        h(
          'li',
          null,
          h(
            'div',
            { class: 'carta-line' },
            h('span', { class: 'dish' }, `${line.quantity} × ${line.name}`),
            h('span', { class: 'leader', 'aria-hidden': 'true' }),
            h('span', { class: 'price' }, euro.format(line.subtotal)),
          ),
        ),
      ),
    ),
    h('div', { class: 'ticket-total' }, h('span', null, 'Total'), h('span', null, euro.format(bill.total))),
  );

  if (!pending) {
    setScreen(
      'Factura',
      back,
      ticket,
      h('div', { class: 'notice info' }, h('p', null, `Pagada con ${bill.payment_method || '¿?'} el ${formatDateTime(bill.close_datetime)}.`)),
    );
    return;
  }

  const payForm = methods.length
    ? h(
        'form',
        {
          class: 'panel',
          onsubmit: onSubmit(async (data) => {
            await api.post(`/api/bills/${bid}/pay`, data);
            toast('Factura cobrada. La mesa vuelve a estar libre.');
            navigate(`#/u/${uid}/r/${rid}/mesas`, { replace: true });
          }),
        },
        h('h2', null, 'Cobrar con'),
        h(
          'div',
          { class: 'choices' },
          methods.map((method) =>
            h('label', { class: 'choice' }, h('input', { type: 'radio', name: 'payment_method_id', value: method.id, required: true }), method.name),
          ),
        ),
        h('button', { class: 'btn', type: 'submit' }, `Cobrar ${euro.format(bill.total)}`),
      )
    : h(
        'div',
        { class: 'notice info' },
        h('p', null, 'Para cobrar necesitas al menos un método de pago (efectivo, tarjeta, bizum…).'),
        h('a', { class: 'btn', href: paymentsHash }, 'Crear un método de pago'),
      );

  const voidBill = guarded(async () => {
    const confirmed = await confirmDialog({
      title: '¿Anular la factura?',
      message: `Se anulará la factura de ${euro.format(bill.total)}. Las comandas volverán a estar abiertas y se podrán modificar.`,
      confirmLabel: 'Anular factura',
      danger: true,
    });
    if (!confirmed) return;
    await api.del(`/api/bills/${bid}`);
    toast('Factura anulada');
    navigate(tableHash, { replace: true });
  });

  setScreen(
    'Factura',
    back,
    ticket,
    payForm,
    h('div', { class: 'danger-zone' }, h('button', { class: 'btn danger-outline', type: 'button', onclick: voidBill }, 'Anular factura')),
  );
}
