

const API_BASE_URL = process.env.REACT_APP_API_URL;

if (!API_BASE_URL) {
  console.error(
    '[config] REACT_APP_API_URL is not set. ' +
    'Create face-similarity-app/frontend/.env and add: ' +
    'REACT_APP_API_URL=http://<backend-host>:5001'
  );
}

console.log('[config] API_BASE_URL:', API_BASE_URL);

export { API_BASE_URL };
