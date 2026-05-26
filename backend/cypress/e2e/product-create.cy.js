describe('Create product', () => {
  it('should create a product by API', () => {
<<<<<<< ours
    cy.loginByApi('admin', 'admin');
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jhi-authenticationToken');
=======
    const productName = `Teclado-${Date.now()}`;

    cy.visit('/');
    cy.loginByApi('admin', 'admin');

    cy.get('@jwtToken').then((token) => {
>>>>>>> theirs
      cy.request({
        method: 'POST',
        url: '/api/products',
        headers: { Authorization: `Bearer ${token}` },
<<<<<<< ours
        body: { name: 'Teclado', price: 150.0, stock: 20 },
      }).its('status').should('eq', 201);
=======
        body: {
          name: productName,
          price: 150.0,
          stock: 20,
        },
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body.name).to.eq(productName);
      });
>>>>>>> theirs
    });
  });
});
