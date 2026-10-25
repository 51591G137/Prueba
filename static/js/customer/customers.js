/* Clientes: elegir uno de la lista o crear uno nuevo. */
import { api } from '../core/api.js';
import { field, h, listOf, loading } from '../core/dom.js';
import { navigate } from '../core/router.js';
import { onSubmit, setScreen, toast } from '../core/ui.js';

const TITLE = 'Reserva tu mesa';

export async function viewCustomers({ stale }) {
  setScreen(TITLE, null, loading());
  const customers = await api.get('/api/customers');
  if (stale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        const customer = await api.post('/api/customers', data);
        toast('Cliente creado');
        navigate(`#/c/${customer.id}`);
      }),
    },
    h('h2', null, 'Nuevo cliente'),
    field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 80, autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Crear cliente'),
  );

  const row = (customer) => h('li', null, h('a', { class: 'row', href: `#/c/${customer.id}` }, h('strong', null, customer.name)));
  setScreen(TITLE, null, h('h2', null, 'Elige un cliente'), listOf(customers, row, 'Todavía no hay clientes. Crea el primero.'), form);
}
