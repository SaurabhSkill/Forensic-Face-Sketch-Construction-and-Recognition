// API Configuration
// Set REACT_APP_API_URL in your .env file to point to the backend.
// Local:  REACT_APP_API_URL=http://localhost:5001
// EC2:    REACT_APP_API_URL=http://<your-ec2-public-ip>:5001
export const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  process.env.REACT_APP_API_BASE_URL ||   // legacy fallback — keep for safety
  'http://localhost:5001';
