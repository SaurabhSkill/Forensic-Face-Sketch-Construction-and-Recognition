import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import MainContainer from './MainContainer';
import '../App-themed.css';

/**
 * AppLayout - Root layout component
 * Provides consistent structure across all pages
 * 
 * Hierarchy:
 * AppLayout (root wrapper)
 *   ├── Header (sticky navigation)
 *   ├── MainContainer (main content area)
 *   │   └── Outlet (page-specific content)
 *   └── Footer (site footer)
 */
const AppLayout = () => {
  return (
    <div className="layout-wrapper">
      <Header />
      <MainContainer>
        <Outlet />
      </MainContainer>
      <Footer />
    </div>
  );
};

export default AppLayout;
