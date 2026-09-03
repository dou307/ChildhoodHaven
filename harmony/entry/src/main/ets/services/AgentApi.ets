import { http } from '@kit.NetworkKit';
import BuildProfile from 'BuildProfile';
import {
  ConfirmedMemory,
  HealthResponse,
  MemoryCandidate,
  TurnRequest,
  TurnResponse
} from '../models/AgentModels';

interface ApiErrorPayload {
  code: string;
  message: string;
  request_id: string;
}

export class AgentApi {
  private static requestSequence: number = 0;

  private static baseUrl(): string {
    const configured = BuildProfile.API_BASE_URL.trim().replace(/\/$/, '');
    if (configured.length === 0) {
      throw new Error('未配置陪伴服务地址');
    }
    if (!BuildProfile.DEBUG && !configured.startsWith('https://')) {
      throw new Error('正式版本必须使用 HTTPS 服务地址');
    }
    return configured;
  }

  private static headers(): Record<string, string> {
    AgentApi.requestSequence += 1;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Request-ID': `harmony-${Date.now()}-${AgentApi.requestSequence}`
    };
    if (BuildProfile.API_TOKEN.length > 0) {
      headers['Authorization'] = `Bearer ${BuildProfile.API_TOKEN}`;
    }
    return headers;
  }

  private static ensureSuccess(responseCode: number, result: Object): void {
    if (responseCode >= 200 && responseCode < 300) {
      return;
    }

    if (typeof result === 'string') {
      let message: string = '';
      let requestId: string = '';
      try {
        const payload = JSON.parse(result) as ApiErrorPayload;
        message = payload.message ?? '';
        requestId = payload.request_id ?? '';
      } catch (_error) {
      }
      if (message.length > 0 && requestId.length > 0) {
        throw new Error(`${message}（追踪号：${requestId}）`);
      }
    }
    throw new Error(`服务返回错误：${responseCode}`);
  }

  static async health(): Promise<HealthResponse> {
    const request = http.createHttp();
    try {
      const response = await request.request(
        `${AgentApi.baseUrl()}/api/v1/health`,
        {
          method: http.RequestMethod.GET,
          header: AgentApi.headers(),
          expectDataType: http.HttpDataType.STRING,
          connectTimeout: 5000,
          readTimeout: 5000
        }
      );
      AgentApi.ensureSuccess(response.responseCode, response.result);
      if (typeof response.result !== 'string') {
        throw new Error('服务返回了无法解析的数据');
      }
      return JSON.parse(response.result) as HealthResponse;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('无法连接陪伴服务');
    } finally {
      request.destroy();
    }
  }

  static async createTurn(conversationId: string, payload: TurnRequest): Promise<TurnResponse> {
    const request = http.createHttp();
    try {
      const response = await request.request(
        `${AgentApi.baseUrl()}/api/v1/conversations/${conversationId}/turns`,
        {
          method: http.RequestMethod.POST,
          header: AgentApi.headers(),
          extraData: JSON.stringify(payload),
          expectDataType: http.HttpDataType.STRING,
          connectTimeout: 10000,
          readTimeout: 60000
        }
      );

      AgentApi.ensureSuccess(response.responseCode, response.result);
      if (typeof response.result !== 'string') {
        throw new Error('服务返回了无法解析的数据');
      }
      return JSON.parse(response.result) as TurnResponse;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('请求陪伴服务失败');
    } finally {
      request.destroy();
    }
  }

  static async confirmMemory(childId: string, candidate: MemoryCandidate): Promise<ConfirmedMemory> {
    const request = http.createHttp();
    try {
      const response = await request.request(
        `${AgentApi.baseUrl()}/api/v1/children/${childId}/memories`,
        {
          method: http.RequestMethod.POST,
          header: AgentApi.headers(),
          extraData: JSON.stringify({ candidate: candidate, guardian_confirmed: true }),
          expectDataType: http.HttpDataType.STRING,
          connectTimeout: 10000,
          readTimeout: 30000
        }
      );
      AgentApi.ensureSuccess(response.responseCode, response.result);
      if (typeof response.result !== 'string') {
        throw new Error('服务返回了无法解析的数据');
      }
      return JSON.parse(response.result) as ConfirmedMemory;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('保存长期记忆失败');
    } finally {
      request.destroy();
    }
  }

  static async listMemories(childId: string): Promise<ConfirmedMemory[]> {
    const request = http.createHttp();
    try {
      const response = await request.request(
        `${AgentApi.baseUrl()}/api/v1/children/${childId}/memories`,
        {
          method: http.RequestMethod.GET,
          header: AgentApi.headers(),
          expectDataType: http.HttpDataType.STRING,
          connectTimeout: 10000,
          readTimeout: 30000
        }
      );
      AgentApi.ensureSuccess(response.responseCode, response.result);
      if (typeof response.result !== 'string') {
        throw new Error('服务返回了无法解析的数据');
      }
      return JSON.parse(response.result) as ConfirmedMemory[];
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('读取长期记忆失败');
    } finally {
      request.destroy();
    }
  }

  static async deleteMemory(childId: string, memoryId: string): Promise<void> {
    const request = http.createHttp();
    try {
      const response = await request.request(
        `${AgentApi.baseUrl()}/api/v1/children/${childId}/memories/${memoryId}`,
        {
          method: http.RequestMethod.DELETE,
          header: AgentApi.headers(),
          connectTimeout: 10000,
          readTimeout: 30000
        }
      );
      AgentApi.ensureSuccess(response.responseCode, response.result);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('删除长期记忆失败');
    } finally {
      request.destroy();
    }
  }
}
