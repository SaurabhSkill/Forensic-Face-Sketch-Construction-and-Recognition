import React from 'react';
import PropTypes from 'prop-types';

/**
 * PageContainer - Individual page content wrapper
 * Provides consistent max-width and responsive padding for page content
 * 
 * Variants:
 * - 'default' (container): 1400px max-width - General content
 * - 'page': 1200px max-width - Content pages
 * - 'content': 900px max-width - Text-heavy content
 * - 'wide': 1600px max-width - Dashboards, data displays
 * - 'full': No max-width - Full-width content
 * 
 * Usage:
 * <PageContainer variant="default">
 *   <h1>Page Title</h1>
 *   <p>Page content...</p>
 * </PageContainer>
 * 
 * With section padding:
 * <PageContainer variant="page" className="section">
 *   Content with vertical padding
 * </PageContainer>
 */
const PageContainer = ({ 
  children, 
  variant = 'default',
  className = '' 
}) => {
  const getContainerClass = () => {
    switch (variant) {
      case 'page':
        return 'page';
      case 'content':
        return 'content';
      case 'wide':
        return 'wide';
      case 'full':
        return 'full';
      case 'default':
      default:
        return 'container';
    }
  };

  return (
    <div className={`${getContainerClass()} ${className}`}>
      {children}
    </div>
  );
};

PageContainer.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['default', 'page', 'content', 'wide', 'full']),
  className: PropTypes.string
};

export default PageContainer;
