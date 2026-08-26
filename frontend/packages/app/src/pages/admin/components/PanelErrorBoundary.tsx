import {Component, type ErrorInfo, type ReactNode} from "react";
import {Alert, Button, Stack, Text} from "@mantine/core";

type Props = {children?: ReactNode; label?: string};
type State = {error: Error | null};

/** 개발 중 섹션 렌더 오류 표시 */
export class PanelErrorBoundary extends Component<Props, State> {
    state: State = {error: null};

    static getDerivedStateFromError(error: Error): State {
        return {error};
    }

    componentDidCatch(error: Error, info: ErrorInfo) {
        console.error(`[${this.props.label ?? "Panel"}]`, error, info.componentStack);
    }

    render() {
        if (this.state.error) {
            return (
                <Alert color="red" title={`${this.props.label ?? "화면"} 렌더 오류`}>
                    <Stack gap="xs">
                        <Text size="sm">{this.state.error.message}</Text>
                        <Button size="xs" variant="light" onClick={() => this.setState({error: null})}>
                            다시 시도
                        </Button>
                    </Stack>
                </Alert>
            );
        }
        return this.props.children;
    }
}
