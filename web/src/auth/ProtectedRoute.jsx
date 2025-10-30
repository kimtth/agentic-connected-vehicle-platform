import { AuthenticatedTemplate, UnauthenticatedTemplate } from '@azure/msal-react';

const ProtectedRoute = ({ children }) => {
  return (
    <>
      <AuthenticatedTemplate>
        {children}
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <div className="container mx-auto max-w-2xl">
          <div className="flex flex-col items-center justify-center min-h-screen text-center">
            <h1 className="text-5xl font-bold mb-4">
              Welcome to Connected Car Platform
            </h1>
            <p className="text-lg text-muted-foreground mb-6">
              Please sign in using the button in the header to access the application
            </p>
            <p className="text-sm text-muted-foreground">
              Click "Sign In" in the top-right corner to continue
            </p>
          </div>
        </div>
      </UnauthenticatedTemplate>
    </>
  );
};

export default ProtectedRoute;