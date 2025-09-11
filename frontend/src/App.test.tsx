import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import App from './App';

const theme = createTheme();

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>
          {component}
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

test('renders PLC Code Generator title', () => {
  renderWithProviders(<App />);
  const titleElement = screen.getByText(/PLC Code Generator/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders navigation items', () => {
  renderWithProviders(<App />);
  expect(screen.getByText('Dashboard')).toBeInTheDocument();
  expect(screen.getByText('Code Editor')).toBeInTheDocument();
  expect(screen.getByText('Projects')).toBeInTheDocument();
  expect(screen.getByText('Monitor')).toBeInTheDocument();
});
