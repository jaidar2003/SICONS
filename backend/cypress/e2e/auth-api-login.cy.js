describe('API login', () => {
  it('should login with /api/authenticate and store token', () => {
<<<<<<< ours
    cy.request('POST', '/api/authenticate', {
      username: 'admin',
      password: 'admin',
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      expect(resp.body.id_token).to.exist;
      cy.window().then((win) => {
        win.localStorage.setItem('jhi-authenticationToken', resp.body.id_token);
      });
    });
=======
    cy.visit('/');
    cy.loginByApi('admin', 'admin');

    cy.window().then((win) => {
      const savedToken = win.localStorage.getItem('jhi-authenticationToken');
      expect(savedToken).to.be.a('string').and.not.be.empty;
    });

    cy.get('@jwtToken').should('be.a', 'string');
>>>>>>> theirs
  });
});
