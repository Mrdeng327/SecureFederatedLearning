const axios = require('axios');
const fs = require('fs');

const API_GATEWAY = 'http://127.0.0.1:8080/ipfs/';

async function getFile(cid) {
    try {
        const fileUrl = `${API_GATEWAY}${cid}`;
        const response = await axios.get(fileUrl, { responseType: 'stream' });

        const filePath = `./downloaded_${cid}.txt`;
        const writer = fs.createWriteStream(filePath);
        response.data.pipe(writer);

        writer.on('finish', () => {
            console.log(`File downloaded: ${filePath}`);
        });
    } catch (error) {
        console.error("Download failed:", error.message);
    }
}

getFile("QmZfqHkfT7KqkXVum8Pvx1RR4rvLrp2gmqXDonrCtyhEv");
