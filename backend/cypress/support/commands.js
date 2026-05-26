<<<<<<< ours
Cypress.Commands.add('loginByApi', (username, password) => {
  cy.request('POST', '/api/authenticate', { username, password }).then((resp) => {
    expect(resp.status).to.eq(200);
    expect(resp.body.id_token).to.exist;
    cy.window().then((win) => {
      win.localStorage.setItem('jhi-authenticationToken', resp.body.id_token);
    });
=======
Cypress.Commands.add('loginByApi', (username = 'admin', password = 'admin') => {
  cy.request({
    method: 'POST',
    url: '/api/authenticate',
    body: { username, password },
    failOnStatusCode: false,
  }).then((response) => {
    expect(response.status, 'auth status').to.eq(200);
    expect(response.body.id_token, 'JWT token').to.be.a('string').and.not.be.empty;

    const token = response.body.id_token;
    cy.window().then((win) => {
      win.localStorage.setItem('jhi-authenticationToken', token);
    });

    return cy.wrap(token, { log: false }).as('jwtToken');
>>>>>>> theirs
  });
});
