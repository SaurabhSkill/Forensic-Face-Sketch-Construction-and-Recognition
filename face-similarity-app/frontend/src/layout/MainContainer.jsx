import React from 'react';
import PropTypes from 'prop-types';

/**
 * MainContainer - Main content wrapper
 * Provides the main content area that grows to fill available space
 * Uses layout-main class for flex: 1 behavior
 * 
 * Usage:
 * <MainContainer>
 *   <PageContainer>
 *     Page content here
 *   </PageContainer>
 * </MainContainer>
 */
const MainContainer = ({ children, className = '' }) => {
  return (
    <main className={`layout-main ${className}`}>
      {children}
    </main>
  );
};

MainContainer.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string
};

export default MainContainer;
