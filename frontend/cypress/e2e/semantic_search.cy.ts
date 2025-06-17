describe("Semantic Search", () => {
  it("returns results when user searches", () => {
    cy.intercept("GET", "/api/v1/search/videos*", {
      statusCode: 200,
      body: {
        data: [
          {
            videoId: "00000000-0000-0000-0000-000000000001",
            title: "Test Video",
            thumbnailUrl: null,
            userId: "user",
            submittedAt: new Date().toISOString(),
            views: 0,
            averageRating: null,
          },
        ],
        pagination: {
          currentPage: 1,
          pageSize: 10,
          totalItems: 1,
          totalPages: 1,
        },
      },
    }).as("search");

    cy.visit("/");
    cy.get('input[aria-label="Search videos"]').type("test{enter}");
    cy.wait("@search");
    cy.contains("Test Video");
  });
}); 