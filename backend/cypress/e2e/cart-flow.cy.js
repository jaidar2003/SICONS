describe('Cart flow', () => {
<<<<<<< ours
  it('should add product to shopping cart', () => {
    cy.loginByApi('admin', 'admin')
    cy.visit('/shopping-cart')
    cy.contains('Agregar producto').click()
    cy.contains('Guardar').click()
    cy.contains('Shopping Cart').should('exist')
  })
})
=======
  it('should open shopping cart after API login', () => {
    cy.visit('/');
    cy.loginByApi('admin', 'admin');

    cy.visit('/shopping-cart');
    cy.contains(/shopping cart/i).should('be.visible');
  });
});
>>>>>>> theirs
