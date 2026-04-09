import { useEffect, useState, useRef } from 'react';
import { io } from 'socket.io-client';

export const useSocket = (url) => {
  const [lastSpike, setLastSpike] = useState(null);
  const socketRef = useRef();

  useEffect(() => {
    socketRef.current = io(url);

    socketRef.current.on('VOLATILITY_SPIKE', (data) => {
      console.log('Nexus Signal: Volatility Spike detected', data);
      setLastSpike(data);
    });

    return () => socketRef.current.disconnect();
  }, [url]);

  return { lastSpike };
};

export const useChronicle = (url) => {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchChronicle = async () => {
    try {
      const resp = await fetch(`${url}/chronicle`);
      const data = await resp.json();
      setEntries(data);
    } catch (err) {
      console.error('Core Logic Failure: External Ledger offline', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChronicle();
    const interval = setInterval(fetchChronicle, 10000); // Polling every 10s
    return () => clearInterval(interval);
  }, [url]);

  return { entries, loading, refresh: fetchChronicle };
};
