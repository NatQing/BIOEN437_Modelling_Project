export const EXAMPLES = {
  "Spec example (6 reactions)": { T: 10, dt: 0.5, text: `# comment (also // comment)
J1: A + B -> C; k1
J2: C -> A + B; k2
J3: 2 A -> D; k3
J4: -> A; k4
J5: D -> ; k5
$X -> A; k6
species A, B, C, D        # optional declarations
const species $X
A = 100; B = 50; C = 0; D = 0; X = 10
k1 = 0.001; k2 = 0.1; k3 = 0.0005; k4 = 2; k5 = 0.05; k6 = 0.2
` },
  "Birth-death (Poisson steady state)": { T: 20, dt: 0.2, text: `# mean = k1/k2 = 10
J1: -> A; k1
J2: A -> ; k2
A = 0
k1 = 5; k2 = 0.5
` },
  "Enzyme kinetics": { T: 100, dt: 1, text: `E + S -> ES; kon
ES -> E + S; koff
ES -> E + P; kcat
E = 20; S = 100; ES = 0; P = 0
kon = 0.005; koff = 0.1; kcat = 0.05
` },
};
