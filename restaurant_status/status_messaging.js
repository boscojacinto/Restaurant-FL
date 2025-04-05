const RequestClient = require'status-js';
/*// or, if it’s a named export from a submodule
// import { RequestClient } from 'status-js/lib/request-client';

// Initialize the client (parameters depend on implementation)
const client = new RequestClient({
  // Example configuration (adjust based on actual API)
  nodeUrl: 'https://waku-node.example.com', // Waku node URL
  timeout: 5000, // Optional timeout in ms
});

// Example: Make a request
async function fetchData() {
  try {
    const response = await client.request({
      method: 'GET', // or 'POST', etc.
      endpoint: '/some-endpoint', // Adjust based on Waku or service API
      data: { key: 'value' }, // Optional payload
    });
    console.log('Response:', response);
  } catch (error) {
    console.error('Error:', error);
  }
}

fetchData();*/