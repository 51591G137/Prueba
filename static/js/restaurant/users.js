/* Usuarios: elegir uno, crear, editar el nombre y borrar. */
import { api } from '../core/api.js';
import { field, h, listOf, loading } from '../core/dom.js';
import { leave, navigate } from '../core/router.js';
import { confirmDialog, guarded, onSubmit, setScreen, toast } from '../core/ui.js';

const TITLE = 'Gestión del restaurante';

export async function viewUsers({ stale }) {
  setScreen(TITLE, null, loading());
  const users = await api.get('/api/users');
  if (stale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        const user = await api.post('/api/users', data);
        toast('Usuario creado');
        navigate(`#/u/${user.id}`);
      }),
    },
    h('h2', null, 'Nuevo usuario'),
    field('Nombre de usuario', h('input', { name: 'username', type: 'text', required: true, maxlength: 80, autocomplete: 'off' })),
    h('button', { class: 'btn', type: 'submit' }, 'Crear usuario'),
  );

  const row = (user) =>
    h(
      'li',
      null,
      h(
        'div',
        { class: 'row' },
        h('a', { class: 'main', href: `#/u/${user.id}` }, h('strong', null, user.username)),
        h('a', { class: 'btn small secondary', href: `#/u/${user.id}/editar`, 'aria-label': `Editar a ${user.username}` }, 'Editar'),
      ),
    );

  setScreen(TITLE, null, h('h2', null, 'Elige un usuario'), listOf(users, row, 'Todavía no hay usuarios. Crea el primero.'), form);
}

export async function viewUserEdit({ params, stale }) {
  const { uid } = params;
  setScreen('Editar usuario', '#/', loading());
  const [user, restaurants] = await Promise.all([api.get(`/api/users/${uid}`), api.get(`/api/users/${uid}/restaurants`)]);
  if (stale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        await api.patch(`/api/users/${uid}`, data);
        toast('Cambios guardados');
        leave('#/');
      }),
    },
    h('h2', null, 'Nombre de usuario'),
    field('Nombre de usuario', h('input', { name: 'username', type: 'text', value: user.username, required: true, maxlength: 80 })),
    h('button', { class: 'btn', type: 'submit' }, 'Guardar cambios'),
  );

  const remove = guarded(async () => {
    const n = restaurants.length;
    const confirmed = await confirmDialog({
      title: `¿Borrar a ${user.username}?`,
      message: n
        ? `Se borrarán también los restaurantes que solo gestiona este usuario (${n} en total), con todas sus mesas, menú, comandas, facturas y reservas. No se puede deshacer.`
        : 'No se puede deshacer.',
      confirmLabel: 'Borrar usuario',
      danger: true,
    });
    if (!confirmed) return;
    await api.del(`/api/users/${uid}`);
    toast('Usuario borrado');
    leave('#/');
  });

  setScreen(
    'Editar usuario',
    '#/',
    form,
    h('div', { class: 'danger-zone' }, h('button', { class: 'btn danger', type: 'button', onclick: remove }, 'Borrar usuario')),
  );
}
