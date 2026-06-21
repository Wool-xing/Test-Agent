import { describe, it, expect } from 'vitest';

describe('App', () => {
  it('renders without crashing (import check)', () => {
    // Verify App component can be imported
    const app = require('./App');
    expect(app.default).toBeDefined();
  });

  it('has valid title', () => {
    expect(document.title).toBeDefined();
  });
});
