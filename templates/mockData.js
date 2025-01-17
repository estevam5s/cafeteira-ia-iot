// Mock data for each route
const mockData = {
  // Guia de uso
  "/guide": {
      basic: {
          commands: [
              "liga - Liga a cafeteira",
              "desliga - Desliga a cafeteira",
              "status - Verifica status atual",
              "temperatura - Mostra temperatura atual",
              "prepara [receita] - Prepara receita específica"
          ],
          interface: [
              "Painel de controle na lateral esquerda",
              "Status em tempo real da cafeteira",
              "Chat interativo para comandos",
              "Menu de navegação superior",
              "Indicadores visuais de temperatura"
          ]
      },
      advanced: {
          features: [
              "Controle de temperatura PID",
              "Programação de horários",
              "Receitas personalizadas",
              "Integração com assistente virtual",
              "Monitoramento remoto"
          ],
          tips: [
              "Mantenha o reservatório sempre limpo",
              "Faça a descalcificação mensalmente",
              "Use água filtrada para melhor sabor",
              "Limpe o porta-filtro após cada uso",
              "Calibre o moedor regularmente"
          ]
      },
      settings: {
          temperature: {
              "Espresso": "92-96°C",
              "Café Coado": "92-96°C",
              "Café Turco": "70-80°C",
              "Chá Verde": "75-80°C",
              "Chá Preto": "90-95°C"
          },
          maintenance: {
              "Limpeza Diária": "Após último uso",
              "Descalcificação": "Mensal",
              "Troca de Filtro": "A cada 3 meses",
              "Calibragem": "Semanal"
          }
      }
  },

  // Receitas
  "/recipes": {
      tradicional: {
          "espresso": {
              name: "Espresso Clássico",
              description: "O tradicional café espresso italiano",
              temperature: "94°C",
              time: "25-30 segundos",
              ingredients: ["18-20g café moído fino"],
              steps: [
                  "Pré-aqueça o porta-filtro",
                  "Dose 18-20g de café",
                  "Tampe com pressão constante",
                  "Extraia por 25-30 segundos",
                  "Deve render 30-35ml"
              ],
              tips: [
                  "Use café recém-moído",
                  "Mantenha pressão constante ao tampar"
              ]
          },
          "coado": {
              name: "Café Coado",
              temperature: "96°C",
              time: "3-4 minutos",
              ingredients: [
                  "30g café moído médio",
                  "500ml água"
              ],
              steps: [
                  "Pré-molhe o filtro",
                  "Adicione o café",
                  "Faça a primeira infusão",
                  "Complete com água em movimentos circulares"
              ]
          }
      },
      especial: {
          "latte": {
              name: "Café Latte",
              temperature: "94°C",
              time: "2-3 minutos",
              ingredients: [
                  "Shot de espresso",
                  "200ml leite"
              ],
              steps: [
                  "Extraia o espresso",
                  "Vaporize o leite (65°C)",
                  "Combine com movimento suave"
              ],
              tips: ["Temperature ideal do leite: 65°C"]
          }
      },
      gelado: {
          "cold_brew": {
              name: "Cold Brew",
              temperature: "Ambiente",
              time: "12-24 horas",
              ingredients: [
                  "100g café moído grosso",
                  "1L água filtrada"
              ],
              steps: [
                  "Misture café e água",
                  "Deixe em infusão na geladeira",
                  "Filtre após 12-24 horas"
              ]
          }
      }
  },

  // Modos de preparo
  "/brewing-methods": {
      "espresso": {
          name: "Espresso",
          equipment: [
              "Máquina de espresso",
              "Porta-filtro",
              "Tamper",
              "Balança de precisão"
          ],
          grind_size: "Fino",
          ratio: "1:2 (café:água)",
          time: "25-30 segundos",
          temperature: "92-96°C",
          steps: [
              "Pré-aqueça o equipamento",
              "Dose 18-20g de café",
              "Distribua uniformemente",
              "Tampe com 15-20kg de pressão",
              "Extraia monitorando tempo e peso"
          ],
          troubleshooting: {
              "Extração rápida": "Ajuste moagem mais fina",
              "Extração lenta": "Ajuste moagem mais grossa",
              "Café amargo": "Diminua temperatura",
              "Café fraco": "Aumente dose ou diminua água"
          }
      },
      "hario_v60": {
          name: "Hario V60",
          equipment: [
              "Cone V60",
              "Filtros de papel",
              "Chaleira com bico",
              "Balança"
          ],
          grind_size: "Médio",
          ratio: "1:15",
          time: "2-3 minutos",
          temperature: "92-96°C",
          steps: [
              "Pré-molhe o filtro",
              "Adicione café moído",
              "Faça bloom por 30s",
              "Complete extração em espiral"
          ]
      }
  },

  // Equipamentos
  "/equipment": {
      controllers: {
          "main_cpu": {
              name: "Controlador Principal",
              function: "Gerenciamento central do sistema",
              specs: [
                  "Processador ARM Cortex-M4",
                  "Frequência 168MHz",
                  "Flash 512KB",
                  "RAM 128KB"
              ],
              pins: {
                  "PA0-PA7": "Sensores analógicos",
                  "PB0-PB1": "Controle bomba",
                  "PC13-PC15": "Interface usuário"
              }
          },
          "pid_controller": {
              name: "Controlador PID",
              function: "Controle preciso de temperatura",
              specs: [
                  "Precisão 0.1°C",
                  "Tempo resposta 100ms",
                  "Auto-tuning",
                  "Proteção superaquecimento"
              ]
          }
      },
      sensors: {
          "temp_1": {
              model: "PT100",
              type: "Temperatura",
              range: "-50°C a 200°C",
              precision: "±0.1°C",
              status: "active"
          },
          "pressure_1": {
              model: "MPXV5004",
              type: "Pressão",
              range: "0-15 bar",
              precision: "±0.1 bar",
              status: "active"
          }
      },
      actuators: {
          "pump_1": {
              model: "ULKA EP5",
              type: "Bomba",
              range: "15 bar",
              status: "active"
          },
          "heater_1": {
              model: "Custom 1500W",
              type: "Resistência",
              range: "1500W",
              status: "active"
          }
      }
  },

  // Manutenção
  "/maintenance-guide": {
      daily: [
          {
              task: "Limpeza do Porta-Filtro",
              description: "Remova e limpe completamente o porta-filtro",
              importance: "Alta",
              frequency: "Após cada uso",
              steps: [
                  "Remova o porta-filtro",
                  "Descarte a borra",
                  "Lave com água quente",
                  "Seque completamente"
              ]
          },
          {
              task: "Purga do Sistema",
              description: "Faça uma purga do sistema de água",
              importance: "Média",
              steps: [
                  "Remova porta-filtro",
                  "Acione água por 2-3 segundos",
                  "Limpe respingos"
              ]
          }
      ],
      weekly: [
          {
              task: "Limpeza Profunda",
              description: "Limpeza com produto específico",
              importance: "Alta",
              frequency: "Semanal",
              steps: [
                  "Insira pastilha de limpeza",
                  "Execute ciclo de limpeza",
                  "Enxágue 3 vezes",
                  "Verifique resíduos"
              ]
          }
      ],
      monthly: [
          {
              task: "Descalcificação",
              description: "Remoção de calcário do sistema",
              importance: "Alta",
              frequency: "Mensal",
              steps: [
                  "Prepare solução descalcificante",
                  "Execute ciclo completo",
                  "Enxágue 5 vezes",
                  "Verifique água clara"
              ]
          }
      ]
  },

  // Documentação
  "/docs": {
      overview: {
          title: "CoffeeAI Control System",
          description: "Sistema integrado de controle para cafeteiras profissionais",
          components: [
              "Interface web responsiva",
              "Controlador PID de temperatura",
              "Sistema de monitoramento em tempo real",
              "Base de dados de receitas",
              "Integração IoT"
          ]
      },
      setup: {
          requirements: {
              hardware: [
                  "Processador 1GHz+",
                  "RAM 512MB+",
                  "Armazenamento 1GB+",
                  "Conexão internet"
              ],
              software: [
                  "Node.js 14+",
                  "MongoDB 4+",
                  "Navegador moderno",
                  "Sistema operacional: Linux/Windows/MacOS"
              ]
          },
          installation: [
              "Clone repositório",
              "Instale dependências",
              "Configure variáveis ambiente",
              "Inicie servidor",
              "Acesse interface web"
          ]
      },
      api: {
          endpoints: [
              {
                  method: "GET",
                  route: "/status",
                  description: "Retorna status atual do sistema"
              },
              {
                  method: "POST",
                  route: "/control",
                  description: "Envia comandos de controle"
              },
              {
                  method: "GET",
                  route: "/recipes",
                  description: "Lista receitas disponíveis"
              }
          ]
      }
  },

  // Funcionalidades
  "/features": {
      basic: {
          title: "Recursos Básicos",
          features: [
              "Controle de temperatura",
              "Temporizador integrado",
              "Receitas pré-programadas",
              "Interface touch",
              "Monitoramento em tempo real"
          ]
      },
      advanced: {
          title: "Recursos Avançados",
          features: [
              "Controle PID customizável",
              "Perfis de temperatura",
              "Integração IoT",
              "Análise de dados",
              "Manutenção preditiva"
          ]
      },
      safety: {
          title: "Recursos de Segurança",
          features: [
              "Proteção contra superaquecimento",
              "Detecção de falhas",
              "Backup de configurações",
              "Alertas em tempo real",
              "Sistema de diagnóstico"
          ]
      }
  }
};

// Export para uso no frontend
if (typeof window !== 'undefined') {
  window.mockData = mockData;
}

// Simulação das funções fetch
async function mockFetch(url) {
  const route = url.startsWith('/') ? url : '/' + url;
  const data = mockData[route];
  
  if (!data) {
      throw new Error(`Route ${route} not found`);
  }

  return {
      json: async () => data,
      ok: true
  };
}

// Substituir fetch global pelo mock
if (typeof window !== 'undefined') {
  window.originalFetch = window.fetch;
  window.fetch = mockFetch;
}