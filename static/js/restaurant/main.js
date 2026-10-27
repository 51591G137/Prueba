/* App de restaurantes. Cada ruta apunta a la pantalla (vista) que la dibuja.
   El orden importa: las rutas más concretas van primero. */
import { startRouter } from '../core/router.js';
import { viewOrderEdit, viewOrderNew } from './orders.js';
import { viewBill } from './payments.js';
import { viewRestaurant } from './restaurant.js';
import { viewRestaurants } from './restaurants.js';
import { viewTableEdit } from './tables.js';
import { viewTableDetail } from './table-detail.js';
import { viewItemEdit } from './menu.js';
import { viewForgotPassword, viewResetPassword, viewUserEdit, viewUsers } from './users.js';

startRouter([
  ['', viewUsers],
  ['olvide-clave', viewForgotPassword],
  ['reset-password', viewResetPassword],
  ['u/:uid/editar', viewUserEdit],
  ['u/:uid', viewRestaurants],
  ['u/:uid/r/:rid/mesa/:tid/editar', viewTableEdit],
  ['u/:uid/r/:rid/mesa/:tid/comanda/nueva', viewOrderNew],
  ['u/:uid/r/:rid/mesa/:tid/comanda/:oid', viewOrderEdit],
  ['u/:uid/r/:rid/mesa/:tid', viewTableDetail],
  ['u/:uid/r/:rid/plato/:iid', viewItemEdit],
  ['u/:uid/r/:rid/factura/:bid', viewBill],
  ['u/:uid/r/:rid/:tab?', viewRestaurant],
]);
