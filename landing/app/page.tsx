import Footer from "./components/Footer";
import Hero from "./components/Hero";
import Nav from "./components/Nav";
import Preview from "./components/Preview";
import RunIt from "./components/RunIt";
import TechStack from "./components/TechStack";
import XFactor from "./components/XFactor";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <Nav />
      <main className="flex-1">
        <Hero />
        <XFactor />
        <Preview />
        <TechStack />
        <RunIt />
      </main>
      <Footer />
    </div>
  );
}
