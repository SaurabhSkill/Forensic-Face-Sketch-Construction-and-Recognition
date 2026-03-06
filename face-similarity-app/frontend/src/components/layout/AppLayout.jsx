import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import '../../App-themed.css';

const AppLayout = () => {
  const location = useLocation();
  
  // Determine active tab from current route
  const getActiveTab = () => {
    const path = location.pathname;
    if (path === '/') return 'home';
    if (path.includes('/sketch')) return 'sketch';
    if (path.includes('/compare')) return 'compare';
    if (path.includes('/search')) return 'search';
    if (path.includes('/database')) return 'criminals';
    if (path.includes('/about')) return 'about';
    if (path.includes('/contact')) return 'contact';
    return 'home';
  };

  return (
    <div className="App">
      <Header activeTab={getActiveTab()} />
      <section className="main-content">
        <div className="layout-container">
          <Outlet />
        </div>
      </section>
      <Footer />
    </div>
  );
};

export default AppLayout;
