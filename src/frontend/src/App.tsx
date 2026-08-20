import { StockChart } from './components/StockChart';
import './App.css';

function App() {
  return (
    <div className="app">
      <StockChart ticker="SBER" />
    </div>
  );
}

export default App;
