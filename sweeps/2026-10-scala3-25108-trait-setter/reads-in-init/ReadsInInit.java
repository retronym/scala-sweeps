// For each class implementing a given trait setter, finds code that can read the overriding
// val while the old compiler (before the fix for scala/scala3#25108) had left the trait's
// value in its field: from the trait setter's call in the trait's `$init$`, through the rest
// of the initialiser that called that `$init$` (a constructor, or `<clinit>` for a top-level
// object, whose fields are static) and the constructors below it, up to the store of the val. Reads are calls of the getter
// (by name, zero arguments) or `getfield`s of the field, found transitively through calls,
// not following calls into the JDK or the Scala standard library.
//
// usage: java -cp <asm-tree:asm> ReadsInInit.java <setter-name> <library jar> <classpath...>

import java.io.*;
import java.util.*;
import java.util.jar.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

public class ReadsInInit {
  static final Map<String, ClassNode> classes = new HashMap<>();
  static final Map<String, String> jarOf = new HashMap<>();

  public static void main(String[] args) throws Exception {
    String setter = args[0];
    String libJar = args[1];
    for (int i = 1; i < args.length; i++)
      for (String p : args[i].split(File.pathSeparator)) if (p.endsWith(".jar")) load(new File(p)); else if (new File(p).isDirectory()) loadDir(new File(p), new File(p));
    String getter = getterName(setter);
    int sites = 0;
    for (ClassNode c : classes.values()) {
      if (!libJar.equals(jarOf.get(c.name))) continue;
      MethodNode impl = find(c, setter, null);
      // skip abstract declarations, and the static forwarders of an object's mirror class
      if (impl == null || (impl.access & (Opcodes.ACC_ABSTRACT | Opcodes.ACC_STATIC)) != 0) continue;
      sites++;
      analyse(c, setter, getter, impl.desc);
    }
    if (sites == 0) System.out.println("no class in " + new File(libJar).getName() + " implements " + setter);
  }

  static String getterName(String setter) {
    // pkg$T$_setter_$x_$eq -> x
    String s = setter.substring(setter.lastIndexOf("$_setter_$") + "$_setter_$".length());
    return s.substring(0, s.length() - "_$eq".length());
  }

  static void analyse(ClassNode c, String setter, String getter, String setterDesc) {
    String fieldType = setterDesc.substring(1, setterDesc.indexOf(')'));
    String getterDesc = "()" + fieldType;
    System.out.println("site " + c.name.replace('/', '.') + "  (" + getter + ": " + fieldType + ")");
    // The trait whose $init$ calls the setter: an interface in c's hierarchy declaring it abstractly.
    String trait = null;
    for (String i : allInterfaces(c)) {
      ClassNode t = classes.get(i);
      if (t != null && find(t, setter, setterDesc) != null && find(t, "$init$", null) != null && callsIn(find(t, "$init$", null), setter)) trait = i;
    }
    if (trait == null) { System.out.println("  ?? no trait $init$ calling " + setter); return; }
    MethodNode init = find(classes.get(trait), "$init$", null);
    List<String> window = new ArrayList<>();
    List<String> hits = new ArrayList<>();
    // 1. the rest of the trait's $init$ after the setter call
    boolean after = false;
    for (AbstractInsnNode n : init.instructions) {
      if (n instanceof MethodInsnNode m && m.name.equals(setter)) { after = true; continue; }
      if (after) scan(trait + ".$init$", n, getter, getterDesc, c.name, hits, new HashSet<>(), 0);
    }
    window.add(trait + ".$init$ after the setter call");
    // 2. From the call of the trait's $init$, in whichever initialiser of c or a superclass makes
    //    it (`<clinit>` for a top-level object, whose fields are static), to the store of c's
    //    field, continuing through the constructors of the classes below that one.
    List<ClassNode> chain = new ArrayList<>(); // c, its superclass, ...
    for (ClassNode k = c; k != null; k = k.superName == null ? null : classes.get(k.superName)) chain.add(k);
    chainNames.clear(); for (ClassNode k : chain) chainNames.add(k.name);
    ClassNode callerCls = null; MethodNode caller = null;
    search: for (ClassNode k : chain)
      for (String mn : List.of("<clinit>", "<init>")) {
        MethodNode m = find(k, mn, null);
        if (callsIn(m, "$init$", trait)) { callerCls = k; caller = m; break search; }
      }
    if (caller == null) { System.out.println("  ?? no initialiser calls " + trait + ".$init$"); return; }
    boolean stored = scanUntilStore(caller, callerCls.name + "." + caller.name, trait, c.name, getter, getterDesc, hits);
    window.add(callerCls.name + "." + caller.name + " after " + trait + ".$init$");
    for (int i = chain.indexOf(callerCls) - 1; i >= 0 && !stored; i--) {
      MethodNode ctor = find(chain.get(i), "<init>", null);
      stored = scanUntilStore(ctor, chain.get(i).name + ".<init>", null, c.name, getter, getterDesc, hits);
      window.add(chain.get(i).name + ".<init> after its super constructor call");
    }
    if (!stored) {
      System.out.println("  not an override: no initialiser of " + c.name + " stores " + getter + " (it inherits the trait's val), so not an affected site");
      return;
    }
    for (String w : window) System.out.println("  window: " + w);
    if (hits.isEmpty()) System.out.println("  no read of " + getter + " in the window");
    else for (String h : new LinkedHashSet<>(hits)) System.out.println("  READ " + h);
  }

  static final Set<String> chainNames = new HashSet<>();

  // Scans `m` from the call of `startAfter.$init$` (from its super constructor call if null) up to
  // a store of `cls.getter`; returns whether it found the store.
  static boolean scanUntilStore(MethodNode m, String where, String startAfter, String cls, String getter, String getterDesc, List<String> hits) {
    boolean started = false;
    for (AbstractInsnNode n : m.instructions) {
      if (!started) {
        if (n instanceof MethodInsnNode i && (startAfter != null ? i.name.equals("$init$") && i.owner.equals(startAfter) : i.name.equals("<init>") && chainNames.contains(i.owner))) started = true;
        continue;
      }
      if (n instanceof FieldInsnNode f && (f.getOpcode() == Opcodes.PUTFIELD || f.getOpcode() == Opcodes.PUTSTATIC) && f.owner.equals(cls) && f.name.equals(getter)) return true;
      scan(where, n, getter, getterDesc, cls, hits, new HashSet<>(), 0);
    }
    return false;
  }

  static void scan(String where, AbstractInsnNode n, String getter, String getterDesc, String cls, List<String> hits, Set<String> seen, int depth) {
    if (n instanceof FieldInsnNode f && (f.getOpcode() == Opcodes.GETFIELD || f.getOpcode() == Opcodes.GETSTATIC) && f.name.equals(getter) && f.owner.equals(cls)) hits.add("read of field " + getter + " in " + where);
    if (!(n instanceof MethodInsnNode m)) return;
    if (m.name.equals("<init>") && chainNames.contains(m.owner)) return; // super constructors ran before the window
    if (m.name.equals(getter) && m.desc.startsWith("()")) { hits.add("call " + m.owner + "." + getter + " in " + where); return; }
    if (depth > 8) return;
    for (MethodNode callee : targets(m, cls)) {
      String key = callee.name + callee.desc + "@" + ownerOf(callee);
      if (!seen.add(key) || callee.instructions == null) continue;
      for (AbstractInsnNode k : callee.instructions) scan(where + " -> " + ownerOf(callee) + "." + callee.name, k, getter, getterDesc, cls, hits, seen, depth + 1);
    }
  }

  static final Map<MethodNode, String> owners = new IdentityHashMap<>();
  static String ownerOf(MethodNode m) { return owners.get(m); }

  // The method a call resolves to in its owner's hierarchy, plus an override in the site's class.
  static List<MethodNode> targets(MethodInsnNode m, String cls) {
    List<MethodNode> out = new ArrayList<>();
    if (skip(m.owner)) return out;
    MethodNode r = resolve(m.owner, m.name, m.desc);
    if (r != null) out.add(r);
    if (m.getOpcode() == Opcodes.INVOKEVIRTUAL || m.getOpcode() == Opcodes.INVOKEINTERFACE) {
      MethodNode o = resolve(cls, m.name, m.desc);
      if (o != null && o != r) out.add(o);
    }
    return out;
  }

  static boolean skip(String owner) {
    String jar = jarOf.get(owner);
    return owner.startsWith("java/") || owner.startsWith("jdk/") || owner.startsWith("sun/") || jar == null
      || jar.contains("scala-library") || jar.contains("scala3-library");
  }

  static MethodNode resolve(String owner, String name, String desc) {
    ClassNode c = classes.get(owner);
    if (c == null || skip(owner)) return null;
    MethodNode m = find(c, name, desc);
    if (m != null && (m.access & Opcodes.ACC_ABSTRACT) == 0) return m;
    if (c.superName != null) { MethodNode s = resolve(c.superName, name, desc); if (s != null) return s; }
    for (String i : c.interfaces) { MethodNode s = resolve(i, name, desc); if (s != null) return s; }
    return null;
  }

  static boolean callsIn(MethodNode m, String name) { return callsIn(m, name, null); }
  static boolean callsIn(MethodNode m, String name, String owner) {
    if (m == null || m.instructions == null) return false;
    for (AbstractInsnNode n : m.instructions)
      if (n instanceof MethodInsnNode i && i.name.equals(name) && (owner == null || i.owner.equals(owner))) return true;
    return false;
  }

  static Set<String> allInterfaces(ClassNode c) {
    Set<String> out = new LinkedHashSet<>();
    Deque<String> todo = new ArrayDeque<>(); todo.add(c.name);
    while (!todo.isEmpty()) {
      ClassNode k = classes.get(todo.pop()); if (k == null) continue;
      if (k.superName != null) todo.add(k.superName);
      for (String i : k.interfaces) if (out.add(i)) todo.add(i);
    }
    return out;
  }

  static MethodNode find(ClassNode c, String name, String desc) {
    for (MethodNode m : c.methods) if (m.name.equals(name) && (desc == null || m.desc.equals(desc))) return m;
    return null;
  }

  static void add(byte[] bytes, String origin) {
    ClassNode c = new ClassNode();
    new ClassReader(bytes).accept(c, ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
    if (classes.putIfAbsent(c.name, c) == null) { jarOf.put(c.name, origin); for (MethodNode m : c.methods) owners.put(m, c.name); }
  }

  static void load(File jar) throws IOException {
    try (JarFile j = new JarFile(jar)) {
      for (JarEntry e : Collections.list(j.entries()))
        if (e.getName().endsWith(".class") && !e.getName().startsWith("META-INF/"))
          try (InputStream in = j.getInputStream(e)) { add(in.readAllBytes(), jar.getPath()); }
    }
  }

  static void loadDir(File root, File dir) throws IOException {
    for (File f : Objects.requireNonNull(dir.listFiles()))
      if (f.isDirectory()) loadDir(root, f);
      else if (f.getName().endsWith(".class")) add(java.nio.file.Files.readAllBytes(f.toPath()), root.getPath());
  }
}
