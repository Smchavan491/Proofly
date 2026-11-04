import React from 'react';
import ReactDOM from 'react-dom/client';
import './style.css';

function App() {
  return (
    <main>
      <h1>Resolve</h1>
      <p>Dispute response workspace</p>
      <section aria-label="Getting started">
        <h2>Your cases will appear here</h2>
        <p>The dashboard is ready for the next development phase.</p>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
