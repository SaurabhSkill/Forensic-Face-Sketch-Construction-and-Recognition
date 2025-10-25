
require('dotenv').config();

module.exports = {
  mongodbUri: process.env.MONGODB_URI,
  jwtSecret: process.env.JWT_SECRET,
  apiKey: process.env.API_KEY,
  port: parseInt(process.env.PORT || '3001', 10)
};
