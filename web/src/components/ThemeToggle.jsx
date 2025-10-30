import { Sun, Moon } from 'lucide-react';

const ThemeToggle = ({ currentTheme, onToggleTheme }) => {
  const isDark = currentTheme === 'dark';

  return (
    <div className="flex items-center gap-4">
      <div className="p-4 flex items-center gap-4 bg-muted rounded-lg border">
        <Sun className={`h-5 w-5 ${!isDark ? 'text-primary' : 'text-muted-foreground'}`} />
        <button
          onClick={onToggleTheme}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            isDark ? 'bg-primary' : 'bg-muted-foreground'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              isDark ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
        <Moon className={`h-5 w-5 ${isDark ? 'text-primary' : 'text-muted-foreground'}`} />
      </div>
      
      <div>
        <h3 className="text-lg font-medium mb-1">
          {isDark ? 'Dark' : 'Light'} Theme
        </h3>
        <p className="text-sm text-muted-foreground">
          {isDark 
            ? 'Perfect for low-light environments and reduced eye strain' 
            : 'Clean and bright interface for better readability'
          }
        </p>
      </div>
    </div>
  );
};

export default ThemeToggle;
